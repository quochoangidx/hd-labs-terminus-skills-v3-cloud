/*
 * Minimal, dependency-free ZIP reader for the browser.
 *
 * The submission bundle can be 200MB+, so we never buffer the whole extracted
 * tree in memory: the caller gets one entry at a time (via `TBUnzip.forEach`)
 * and streams each file straight to disk through the File System Access API.
 *
 * Decompression:
 *   - method 0 (stored)  → copy the bytes as-is.
 *   - method 8 (deflate) → DecompressionStream("deflate-raw"), a native browser
 *     API (no library). Everything Snorkel's zip uses in practice.
 *
 * Central-directory driven (same as `unzip`): we read the End Of Central
 * Directory record from the tail, walk the central directory, then seek each
 * local header for the compressed data. Zip64 EOCD is handled for the offsets
 * so large archives still parse.
 */
(function (root) {
  "use strict";

  var SIG_EOCD = 0x06054b50; // End Of Central Directory
  var SIG_EOCD64 = 0x06064b50; // Zip64 EOCD
  var SIG_EOCD64_LOC = 0x07064b50; // Zip64 EOCD locator
  var SIG_CEN = 0x02014b50; // Central directory file header
  var SIG_LOC = 0x04034b50; // Local file header

  function u32(dv, o) { return dv.getUint32(o, true); }
  function u16(dv, o) { return dv.getUint16(o, true); }

  // Zip64 stores 64-bit values; JS numbers are safe up to 2^53 which is plenty
  // for archive offsets/sizes we care about.
  function u64(dv, o) {
    var lo = dv.getUint32(o, true);
    var hi = dv.getUint32(o + 4, true);
    return hi * 0x100000000 + lo;
  }

  function findEocd(dv) {
    // EOCD is at the very end unless there is a trailing comment (max 65535).
    var len = dv.byteLength;
    var minPos = Math.max(0, len - 22 - 0xffff);
    for (var p = len - 22; p >= minPos; p--) {
      if (u32(dv, p) === SIG_EOCD) return p;
    }
    throw new Error("Not a zip file (no EOCD record found).");
  }

  // Returns { count, cdOffset, cdSize }.
  function readDirectoryMeta(dv) {
    var eocd = findEocd(dv);
    var count = u16(dv, eocd + 10);
    var cdSize = u32(dv, eocd + 12);
    var cdOffset = u32(dv, eocd + 16);

    // Zip64: the classic EOCD holds 0xffffffff sentinels; the real values live
    // in the Zip64 EOCD pointed at by the locator just before the EOCD.
    var needs64 = count === 0xffff || cdOffset === 0xffffffff || cdSize === 0xffffffff;
    if (needs64 && eocd - 20 >= 0 && u32(dv, eocd - 20) === SIG_EOCD64_LOC) {
      var z64 = u64(dv, eocd - 20 + 8);
      if (z64 + 4 <= dv.byteLength && u32(dv, z64) === SIG_EOCD64) {
        count = u64(dv, z64 + 32);
        cdSize = u64(dv, z64 + 40);
        cdOffset = u64(dv, z64 + 48);
      }
    }
    return { count: count, cdOffset: cdOffset, cdSize: cdSize };
  }

  // Parse the central directory into a list of entry descriptors.
  function readEntries(buf) {
    var dv = new DataView(buf);
    var meta = readDirectoryMeta(dv);
    var entries = [];
    var p = meta.cdOffset;
    var decoder = new TextDecoder("utf-8");

    for (var i = 0; i < meta.count; i++) {
      if (u32(dv, p) !== SIG_CEN) break;
      var method = u16(dv, p + 10);
      var compSize = u32(dv, p + 20);
      var uncompSize = u32(dv, p + 24);
      var nameLen = u16(dv, p + 28);
      var extraLen = u16(dv, p + 30);
      var commentLen = u16(dv, p + 32);
      var localOffset = u32(dv, p + 42);
      var nameBytes = new Uint8Array(buf, p + 46, nameLen);
      var name = decoder.decode(nameBytes);

      // Walk the extra field for the Zip64 record (0x0001) that overrides any
      // 0xffffffff sentinel in size / offset.
      var ep = p + 46 + nameLen;
      var eend = ep + extraLen;
      while (ep + 4 <= eend) {
        var hid = u16(dv, ep);
        var hsz = u16(dv, ep + 2);
        if (hid === 0x0001) {
          var q = ep + 4;
          if (uncompSize === 0xffffffff) { uncompSize = u64(dv, q); q += 8; }
          if (compSize === 0xffffffff) { compSize = u64(dv, q); q += 8; }
          if (localOffset === 0xffffffff) { localOffset = u64(dv, q); q += 8; }
        }
        ep += 4 + hsz;
      }

      entries.push({
        name: name,
        method: method,
        compSize: compSize,
        uncompSize: uncompSize,
        localOffset: localOffset,
        isDir: /\/$/.test(name)
      });
      p += 46 + nameLen + extraLen + commentLen;
    }
    return entries;
  }

  // Resolve where the compressed bytes actually start (local header lies about
  // name/extra lengths sometimes, so re-read them from the local header).
  function compressedSlice(buf, entry) {
    var dv = new DataView(buf, entry.localOffset, 30);
    if (dv.getUint32(0, true) !== SIG_LOC) {
      throw new Error("Bad local header for " + entry.name);
    }
    var nameLen = dv.getUint16(26, true);
    var extraLen = dv.getUint16(28, true);
    var start = entry.localOffset + 30 + nameLen + extraLen;
    return new Uint8Array(buf, start, entry.compSize);
  }

  async function inflateRaw(bytes) {
    var ds = new DecompressionStream("deflate-raw");
    var writer = ds.writable.getWriter();
    writer.write(bytes);
    writer.close();
    var out = await new Response(ds.readable).arrayBuffer();
    return new Uint8Array(out);
  }

  // Decompress one entry to a Uint8Array.
  async function entryBytes(buf, entry) {
    var raw = compressedSlice(buf, entry);
    if (entry.method === 0) return raw;
    if (entry.method === 8) return inflateRaw(raw);
    throw new Error("Unsupported compression method " + entry.method + " for " + entry.name);
  }

  // High level: iterate every file entry, decompress it, and hand
  // (relativePath, Uint8Array) to `cb`. Directory entries are skipped (the
  // caller creates folders on demand from the file paths).
  async function forEach(buf, cb, onProgress) {
    var entries = readEntries(buf);
    var files = entries.filter(function (e) { return !e.isDir; });
    for (var i = 0; i < files.length; i++) {
      var e = files[i];
      var data = await entryBytes(buf, e);
      await cb(e.name, data);
      if (onProgress) onProgress(i + 1, files.length, e.name);
    }
    return files.length;
  }

  root.TBUnzip = { readEntries: readEntries, entryBytes: entryBytes, forEach: forEach };
})(typeof self !== "undefined" ? self : this);
