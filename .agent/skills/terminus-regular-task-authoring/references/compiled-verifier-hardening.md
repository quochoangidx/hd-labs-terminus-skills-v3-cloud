# Compiled-language verifier hardening

How a verifier that must compile and run candidate code keeps
`protected_ground_truth` and `sound_verifier` clear. Every technique here was
read out of `cairnlift-fold-and-mend` (Java 21), which cleared the platform
quality panel on all five axes. The shape carries over to any language where the
verifier builds the candidate's sources: Java, Kotlin, Go, Rust, C/C++.

The threat is concrete: in separate mode the candidate's code still runs
**inside the verifier container**, and the compiler itself runs as root.

---

## 1. The compiler runs as root, so give it nothing to run

- `cd /tmp` (or any directory the candidate never wrote) before the first
  compile. `javac`'s default class path is the working directory.
- Compile the candidate with the processor path shut and an explicit empty
  class path: `javac -proc:none -cp "" -d "$yard/app" $(find /app/src/main/java -name '*.java')`.
  Otherwise an annotation processor the candidate shipped runs as root at
  compile time. Compile the probe against the candidate's classes only:
  `javac -proc:none -processorpath "" -cp "$yard/app" -d "$yard/kit" /tests/Probe.java`.
- The equivalents elsewhere: no `build.rs` or proc-macro crate from the
  candidate compiled as root in Rust, no `go generate`, no candidate Makefile run
  by root.
- Put both compile outputs in a fresh `mktemp -d` yard, and `chmod -R a+rX` only
  that yard.

## 2. Close the source tree before any candidate code runs

Once the sources are compiled, `chmod 700 /app`. Nothing the candidate left
beside the sources (a helper program, a table of answers) can then be read or
run while the probe drives the classes. A policy test asserts both halves: the
mode bits, and that the sandbox user's `ls /app` fails.

## 3. Candidate code runs as a user who owns nothing, with nothing to reach for

- A dedicated system user in `tests/Dockerfile`
  (`useradd --system --uid 12000 --user-group --no-create-home --shell /usr/sbin/nologin sandbox`),
  and every candidate process drops to it with `setpriv --reuid --regid --clear-groups`.
- Children get an empty environment: `PATH=""`, `HOME=/nonexistent`, a fixed
  `LANG`. Name every binary the verifier needs by absolute path.
- In the verifier image, make shells and interpreters root-only (`chmod 750`
  on `/bin/sh`, `/bin/dash`, `/bin/bash`, `python3*`, `perl`, `awk`). The
  candidate's code then cannot shell out to do its work, even though the
  language's process API is present.
- Put the probe **first** on the run-time class path, so a candidate class
  cannot shadow it.
- `chmod 700 /tests /logs/verifier` before the first candidate process starts.
- On `--no-new-privs`: `quality-panel-examples.md` states that its absence alone
  is not a finding without a reachable escalation. Use it anyway when setuid or
  capability-bearing binaries remain in the image.

## 4. The reward is always written, and only by root

Do not `set -e` in `test.sh`. A failing compile or pytest must still reach the
reward write. Write `1` only on a zero pytest exit, after every candidate process
has ended. A comment that explains the missing `set -e` is fine. Section 2 of
`AGENTS.md` records a gate that once read that comment as the flag itself.

## 5. "Keep the public surface" is checked against the compiled artifact

- Ship a snapshot of the published surface in the verifier image. For Java that
  is `javap -public -constants` over every shipped class (`tests/api.txt`).
- Compare per class: the declaration line, plus the **set** of members. Using a
  set means moving a method inside a file is not a violation, while renaming,
  retyping, adding or dropping one is.
- Then read **every** class the build produced, nested and anonymous ones
  included, and fail on any public type that is not in the snapshot. Comparing
  only the shipped names misses a helper class the candidate published beside
  them.

## 6. Restrictions are audited where they bind: in the compiled code

Source text does not decide what a program reaches at run time
(`contract-closure.md` §4). The sample audits both levels:

- **Source level**, for what source genuinely decides: every `.java` under the
  *whole* `/app` tree, not just the build root, sits in the one permitted
  directory and declares the one package. The audited set is then asserted equal
  to the compiled set. Translate Unicode escapes, and strip comments and
  literals, before tokenising. Text in a string literal authorises nothing.
- **Compiled level**, for reflection, native code, process starts and
  namespaces: `javap -v -p` over every class, batched. Read `Class` entries,
  descriptors and `Methodref`/`InterfaceMethodref` owners from the constant
  pool, never string constants. A call is judged by the type that owns it, so a
  candidate helper named `invoke` is not mistaken for reflection, and a
  reflective call cannot hide behind an alias. Reject `ACC_NATIVE` in flags.
- **Allow what the compiler emits itself**, and say so in the instruction: the
  `java.io.PrintStream` behind `System.out`, and the `java.lang.invoke`
  bootstraps for string concatenation and lambdas (`StringConcatFactory`,
  `LambdaMetafactory` and the handle types). Without that list, an honest
  solution that joins two strings fails a rule nobody wrote down.

## 7. Numbers across a language boundary

Where the authority fixes the text (a report line, `to six places`), compare
the text exactly. Where the Python test model computes a value itself, compare
the numbers to the written precision rather than as text, because Python and
Java round a tie in the last place differently. Name that reason in
`verification_explanation`, so a reviewer does not read the tolerance as a
loophole.

## 8. One probe program, many scenes

Drive the candidate through one compiled probe that takes a scene name and
prints JSON, run once per scene as the sandbox user. pytest then reads only what
the candidate's code answered. The probe is verifier code: it lives in
`tests/`, it is copied into the verifier image, and it is never visible to the
agent.
