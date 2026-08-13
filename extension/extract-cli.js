#!/usr/bin/env node
/*
 * extract-cli.js — offline companion to the extension.
 *
 * Converts a saved review payload into <task_id>.md using the exact same
 * generator the extension uses (generate.js).
 *
 * Usage:
 *   node extract-cli.js <input.har|input.json> [outDir]
 *
 * Accepts:
 *   - a raw review API response  ({ "tasks": [ ... ] })
 *   - a single task object
 *   - a .har capture (scans every response body, base64 or plain, for review payloads)
 *
 * Writes one <uuid>.md file per task into outDir (default: current directory).
 */
"use strict";

var fs = require("fs");
var path = require("path");
var TBGen = require("./generate.js");

function die(msg) {
  console.error(msg);
  process.exit(1);
}

function looksLikeTasks(obj) {
  return obj && Array.isArray(obj.tasks) && obj.tasks.length &&
    obj.tasks[0] && obj.tasks[0].task_documents;
}

function collectFromHar(har) {
  var out = [];
  var entries = (har.log && har.log.entries) || [];
  entries.forEach(function (e) {
    try {
      var c = e.response && e.response.content;
      if (!c || !c.text) return;
      var raw = c.encoding === "base64" ? Buffer.from(c.text, "base64").toString("utf8") : c.text;
      var obj = JSON.parse(raw);
      if (looksLikeTasks(obj)) out.push.apply(out, obj.tasks);
    } catch (e2) { /* not JSON / not a review payload */ }
  });
  return out;
}

function main() {
  var input = process.argv[2];
  var outDir = process.argv[3] || ".";
  if (!input) die("Usage: node extract-cli.js <input.har|input.json> [outDir]");
  if (!fs.existsSync(input)) die("File not found: " + input);

  var text = fs.readFileSync(input, "utf8");
  var data;
  try { data = JSON.parse(text); } catch (e) { die("Input is not valid JSON/HAR: " + e.message); }

  var tasks;
  if (data.log && data.log.entries) tasks = collectFromHar(data);
  else tasks = TBGen.extractTasks(data);

  if (!tasks.length) die("No review tasks found in input.");

  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  // De-duplicate by task_id (HAR may hold the same response twice).
  var seen = {};
  var written = 0;
  tasks.forEach(function (t) {
    var id = TBGen.taskId(t);
    if (seen[id]) return;
    seen[id] = true;
    var md = TBGen.generateMarkdown(t);
    var file = path.join(outDir, id + ".md");
    fs.writeFileSync(file, md);
    console.log("wrote " + file + " (" + md.length + " chars)");
    written++;
  });
  console.log("done: " + written + " file(s).");
}

main();
