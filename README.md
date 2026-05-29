# Terminus_Task_Skill

Bộ kỹ năng hỗ trợ tạo Terminus Regular task từ issue/PR upstream đã đóng hoặc đã merge. Bộ này tập trung vào quy trình clone bug thật thành task `tbrain-*`, viết prompt tự nhiên như người thật, thiết kế verifier đủ chặt, validate bằng Harbor, và đóng gói ZIP đúng chuẩn Snorkel Platform.

---

> **Disclaimer**: Đây là bộ workflow cá nhân để tạo và kiểm tra task Terminus. Nội dung được tổng hợp từ tài liệu local trong `docs/`, task mẫu, và kinh nghiệm debug CI/Harbor. Nếu rule trong Snorkel Platform thay đổi, ưu tiên feedback mới nhất từ CI/Harbor/LLMaJ.

---

## Tổng quan

Repo này cung cấp các skill để tạo task end to end. Quy tắc mới: tách rõ `mine` và `clone` để giảm quota, tăng tốc sản xuất nhiều task, và tránh Codex đọc lại repo quá nhiều lần.

| # | Tên kỹ năng | Slash command gợi ý | Mô tả |
|---|---|---|---|
| 1 | **Task Miner** | `/task-miner` | Mine metadata/scoring từ closed issue/PR upstream quota thấp-trung bình, không tạo task |
| 2 | **Task Clone** | `/task-clone` | Transform mined candidate thành Terminus Regular task trong `workspace/tbrain-<problem-slug>` |
| 3 | **Terminus Regular Task Authoring** | `/terminus-regular-task-authoring` | Tạo/audit cấu trúc Regular task theo Platform Submission Guide |
| 4 | **Issue To Regression Test** | `/issue-to-regression-test` | Biến issue/PR thành verifier tests hành vi, có regression và anti-shortcut |
| 5 | **Terminus Hard Python Verifier** | `/terminus-hard-python-verifier` | Viết verifier/oracle cho Python debugging task đủ khó |
| 6 | **Upstream Repo Sanitizer** | `/upstream-repo-sanitizer` | Làm sạch `environment/repo`, giữ build context dưới giới hạn CI |
| 7 | **Task Harbor Runner** | `/task-harbor-runner` | Chạy và debug Harbor: oracle, nop, CI checks, real agents |
| 8 | **Task Zip Submit** | `/task-zip-submit` | Đóng gói ZIP sạch, đúng cấu trúc, không dính macOS junk |

---

## Cấu trúc thư mục

```text
terminus-bench/
|-- README.md
|-- .gitignore
|-- docs/                         # Tài liệu Terminus/Snorkel local
|-- skills/                       # Skill source chính
|   |-- task-clone/SKILL.md
|   |-- task-miner/SKILL.md
|   |-- terminus-regular-task-authoring/SKILL.md
|   |-- issue-to-regression-test/SKILL.md
|   |-- terminus-hard-python-verifier/SKILL.md
|   |-- upstream-repo-sanitizer/SKILL.md
|   |-- task-harbor-runner/SKILL.md
|   `-- task-zip-submit/SKILL.md
|-- .codex/skills/                # Bản sync cho Codex trong workspace
|-- .claude/skills/               # Bản sync cho Claude trong workspace
|-- mined-candidates/
    |   |   `-- index.jsonl        # Registry chống trùng issue/PR/candidate
`-- workspace/                    # Task, reports, ZIP local; bị .gitignore
    |-- tbrain-*/
    |-- reports/
    |   `-- tbrain-*/
    `-- submissions/
```

Task clone, Harbor reports và submission ZIP đều để trong `workspace/`. Đây là khu vực local, không đẩy lên git. `.gitignore` đã ignore nguyên thư mục `/workspace/`.

---

## Quy trình làm việc (Workflow)

Các skill được thiết kế để phối hợp theo thứ tự sau:

```text
task-miner                         [mine metadata/scoring, không tạo task]
        ↓
workspace/reports/mined-candidates/<candidate>.json
        ↓
task-clone                         [transform candidate thành task]
        ↓
upstream-repo-sanitizer
        ↓
issue-to-regression-test
        ↓
terminus-hard-python-verifier
        ↓
terminus-regular-task-authoring    [audit/sửa cấu trúc task]
        ↓
task-harbor-runner
        ↓
task-zip-submit
```

**NOTE**: Nếu đã có issue/PR URL cụ thể, có thể bắt đầu từ `task-clone`. Nếu cần tìm candidate trước, dùng `task-miner`.

### Thứ tự triển khai

1. **task-miner**: Quét closed issue/PR upstream, ưu tiên nguồn quota thấp-trung bình như `pytest-dev/pytest`, `pypa/pip`, `django/django`, và chọn lọc `pandas-dev/pandas`. Skill này chỉ xuất artifact ngắn ở `workspace/reports/mined-candidates/`, không viết Dockerfile, verifier, oracle, hay task folder.
2. **task-clone**: Đọc mined candidate artifact rồi transform thành task. Nếu artifact đã đủ thông tin, không re-mine GitHub và không quét lại lịch sử repo.
3. **upstream-repo-sanitizer**: Clone/stage repo vào `environment/repo`, prune file nặng, xóa file giống secret, kiểm tra `environment/ <= 100 MiB`.
4. **issue-to-regression-test**: Chuyển bug upstream thành verifier tests: direct regression, boundary, normal behavior, anti-shortcut.
5. **terminus-hard-python-verifier**: Hoàn thiện `tests/test_outputs.py`, `tests/test.sh`, oracle pattern và coverage cho Python Hard task.
6. **terminus-regular-task-authoring**: Audit `instruction.md`, `task.toml`, Dockerfile, oracle và verifier theo Platform Submission Guide.
7. **task-harbor-runner**: Chạy `harbor run -a oracle`, `harbor run -a nop`, `harbor tasks check`, rồi follow feedback nếu fail.
8. **task-zip-submit**: Dọn cache/macOS junk, zip đúng contents của task folder, verify archive trước khi upload.

### Phối hợp giữa các kỹ năng

- **task-miner** là bước lọc nhanh. Dừng khi đã có candidate đủ điểm, tránh over-search.
- **task-clone** là bước transform chính. Khi người dùng đưa `mined_candidate.json`, bắt đầu từ đây và không mine lại.
- **upstream-repo-sanitizer** chạy trước khi build Docker để tránh fail vì build context quá lớn hoặc file bị blacklist.
- **issue-to-regression-test** và **terminus-hard-python-verifier** nên dùng cùng nhau: một skill chuyển issue thành test cases, skill còn lại chuẩn hóa verifier cho Terminus.
- **task-harbor-runner** phải follow feedback cụ thể từ Docker/Harbor/CI trước khi tự đoán lỗi.
- **task-zip-submit** chỉ chạy sau khi oracle pass, nop fail, và CI/LLMaJ không còn blocker. ZIP chỉ được chứa các file/folder mà Platform Submission Guide yêu cầu.

---

## Quy tắc quan trọng

### 1) Quy tắc đặt tên task

Task folder phải có dạng:

```text
tbrain-<problem-slug>
```

Không nhét tên repo/tool/domain vào slug nếu nó chỉ là nguồn của task.

Folder thực tế được tạo dưới:

```text
workspace/tbrain-<problem-slug>/
```

Ví dụ:

- Đúng: `tbrain-maxfail-teardown-reporting`
- Sai: `tbrain-pytest-maxfail-teardown-reporting`
- Đúng: `tbrain-timezone-cutoff-reconciliation`
- Sai: `tbrain-python-timezone-cutoff-reconciliation`

Tên task nên nói về lỗi hoặc hành vi cần sửa, không nói về source repo.

### 2) Quy tắc `instruction.md`

`instruction.md` phải nghe như người thật giao bug cho coding agent, không giống checklist do LLM viết.

Nên có:

- 1-3 đoạn ngắn
- triệu chứng hiện tại
- hành vi mong muốn có thể quan sát được
- absolute paths nếu nhắc file/path
- exact string hoặc schema chỉ khi verifier thật sự assert chúng

Tránh:

- issue URL, PR number
- tên test upstream
- `solution/`, `tests/`, `task.toml`, rubric
- hướng dẫn sửa file nào, function nào, helper nào
- bullet list dài kiểu "must X, must Y"
- tên task trong prompt

Trước khi lưu, chạy prompt sanitizer:

- bỏ issue URL, PR number, commit hash
- bỏ tên upstream test hoặc fixture lấy từ PR
- bỏ internal function/helper name nếu không phải public API
- bỏ hint triển khai như "sửa hàm X" hoặc "đổi biến Y"
- bỏ ngôn ngữ benchmark như verifier, oracle, hidden tests, rubric, CI

Ví dụ tốt:

```md
The package in `/app` mishandles fixture teardown errors when a run stops early after `--maxfail=1`. A user project with a failing test and a session-scoped fixture that fails during teardown currently loses the teardown error in the final report.

Fix it so `python -m pytest ... --maxfail=1 --junitxml=<path>` still stops before running later tests, but reports both the original test failure and the fixture teardown error in the terminal output and JUnit XML. Do not change the user project's tests.
```

### 3) Quy tắc Docker/build context

Giới hạn CI:

- `environment/` tối đa `100 MiB` tổng cộng
- mỗi file trong `environment/` tối đa `50 MiB`

Lý do: Docker build context phải nhẹ, reproducible, cacheable và lazy-pull friendly. Nếu clone nguyên repo quá lớn, CI sẽ fail ngay.

Dockerfile cần:

- `FROM ...@sha256:<digest>`
- cài `tmux` và `asciinema`
- pin package versions
- không `COPY tests/`
- không `COPY solution/`
- không tạo `/tests`, `/oracle`, `/solution`, `/logs/verifier`

### 4) Quy tắc verifier

Verifier phải:

- dùng Python `pytest`
- test behavior, không test implementation bằng cách grep source
- mỗi `def test_*` có docstring
- map với requirement trong `instruction.md`
- luôn ghi `/logs/verifier/reward.txt`

Verifier matrix nên có:

- direct regression
- boundary/ordering variant
- normal behavior preservation
- anti-shortcut case
- crash-resistance/no raw traceback
- output schema/format check nếu task có JSON/XML/CSV/report

Không assert source-code shape, function name nội bộ, hoặc exact implementation.

### 5) Quy tắc tiết kiệm quota

Không dùng một phiên Codex để mine nhiều issue rồi clone full task liên tục. Tách làm hai pha:

```text
mine  = metadata-only
clone = transformation-only
```

Trong mine:

- không đọc quá 10 file nếu chưa cần
- không đi quá 3 commit quanh fix
- không chạy full test suite
- dừng khi có reproducer, touched files, và điểm candidate đủ tốt

Trong clone:

- dùng artifact đã mine
- chỉ đọc touched files và support files cần thiết
- ghi notes ngắn vào `workspace/reports/<task-slug>/`
- không mang raw diff dài trong context nếu không cần

Repo lớn như TypeScript, go-ethereum, PyTorch, NumPy, pandas cần sparse/focused staging trước khi viết verifier.

### 6) Quy tắc chống trùng candidate

Khi nhiều người cùng dùng skill, rất dễ đụng cùng PR/issue tốt. Trước khi mine sâu hoặc clone, check registry:

```text
mined-candidates/index.jsonl
```

Mỗi candidate nên có một dòng JSON compact:

```json
{"repo":"pytest-dev/pytest","issue_or_pr_id":"14465","source_url":"...","fixing_commit":"...","parent_commit":"...","bug_signature":"maxfail session fixture teardown reporting","task_slug":"tbrain-maxfail-teardown-reporting","status":"mined","rejection_reason":null}
```

Key chống trùng:

- `repo + issue_or_pr_id`
- `repo + fixing_commit`
- `repo + bug_signature`

Nếu team có registry chung qua private repo, Sheet, Notion, hoặc Airtable thì check registry chung trước local. Candidate có status `claimed`, `cloned`, hoặc `submitted` thì bỏ qua, trừ khi người dùng cố ý muốn làm variant khác rõ ràng.

### 7) Nguồn mine ưu tiên

Ưu tiên repo có quota burn thấp tới trung bình:

| Repo | Mức quota | Ghi chú |
|---|---|---|
| `pytest-dev/pytest` | thấp | Fixture, collection, reporting, assertion rewriting |
| `pypa/pip` | thấp-trung bình | Resolver, cache/wheel, requirement parsing, install report offline |
| `django/django` | trung bình | ORM SQLite, forms, migrations, templates, management commands |
| `pandas-dev/pandas` | trung bình-cao, chọn lọc | Chỉ lấy bug tiny dataframe, indexing/groupby/merge/datetime/parser, không rebuild extension |

Các repo nặng như TypeScript, go-ethereum, PyTorch, Ray, NumPy vẫn dùng được, nhưng phải bật heavy-repo mode:

- chỉ mine tối đa 1 candidate nặng mỗi phiên
- đọc tối đa 5 file trước khi quyết định tiếp tục
- đọc tối đa 2 commit quanh fix
- không chạy full test/build suite
- phải có repo slimming plan trước khi clone
- verifier kỳ vọng dưới 60 giây
- Docker build context sau slimming phải có khả năng dưới 100 MiB

Reject nếu candidate cần GPU, browser, database, network, cluster, rebuild lớn, hoặc không có reproducer nhỏ offline.

### 8) Quy tắc hardness thực nghiệm

Độ khó của task được chấm bằng pass-rate agent, không chỉ bằng cảm giác codebase phức tạp.

Downgrade hoặc bỏ candidate nếu:

- oracle patch dự kiến chỉ dưới khoảng 10 dòng meaningful trong một file rõ ràng
- verifier chủ yếu là nhiều biến thể của cùng một nhánh điều kiện
- prompt cho agent grep ra đúng symbol/hook quá dễ
- difficulty check cho thấy một frontier agent pass `5/5`
- aggregate real-agent pass rate `>= 80%`

Timeout không đủ để chứng minh Hard. Task Hard tốt nên làm agent tạo patch sai hoặc thiếu vì interaction logic, không phải chỉ kẹt vì môi trường hay tooling.

### 9) Quy tắc Harbor feedback

Nếu Docker, Harbor hoặc CI đưa ra instruction cụ thể, đọc và follow feedback đó trước khi đoán lỗi.

Ví dụ:

- `Cannot connect to Docker daemon` → mở Docker Desktop hoặc kiểm tra socket.
- thiếu digest → pin `FROM ...@sha256:<digest>`.
- build context quá lớn → prune `environment/`.
- reward block fail → sửa `tests/test.sh` theo skeleton.
- LLMaJ nói tests assert hành vi chưa có trong prompt → sửa `instruction.md` hoặc bỏ test đó.

---

## Hướng dẫn từng kỹ năng

### 1) Task Clone

- **Slash command gợi ý**: `/task-clone`
- **Input**: Ưu tiên `mined_candidate.json`; nếu chưa có thì dùng GitHub issue URL, PR URL, `owner/repo`, hoặc mô tả task muốn clone.
- **Output**: Folder `workspace/tbrain-<problem-slug>/`.
- **Mục tiêu**:
  - Transform một bug upstream thật thành Terminus Regular task.
  - Không re-mine GitHub nếu mined artifact đã đủ thông tin.
  - Chọn commit trước fix để stage vào `environment/repo`.
  - Sanitize prompt để không leak issue/PR/commit/test name/hint fix.
  - Đặt tên task đúng dạng `tbrain-<problem-slug>`.
  - Tạo verifier matrix có regression, edge, preservation, anti-shortcut, crash-resistance.
- **Khi nào dùng**: Khi đã có mined candidate hoặc issue/PR cụ thể đủ tốt để transform thành task.

---

### 2) Task Miner

- **Slash command gợi ý**: `/task-miner`
- **Input**: Repo upstream, GitHub issue/PR URL, hoặc để trống thì mặc định dùng `pytest-dev/pytest`.
- **Output**: Compact artifact ở `workspace/reports/mined-candidates/<slug>.json`.
- **Mục tiêu**:
  - Tìm và chấm điểm bug upstream đủ khó.
  - Chỉ mine metadata/scoring, không dựng task, Dockerfile, verifier, oracle.
  - Ưu tiên `pytest-dev/pytest`, `pypa/pip`, `django/django`, và `pandas-dev/pandas` chọn lọc.
  - Loại docs-only, typo-only, dependency bump, CI-only.
  - Dừng sớm khi có reproducer, touched files, parent/fixing commit và score đủ tốt.
- **Khi nào dùng**: Khi chưa có issue/PR cụ thể và muốn mine candidate với chi phí quota thấp-trung bình.

---

### 3) Terminus Regular Task Authoring

- **Slash command gợi ý**: `/terminus-regular-task-authoring`
- **Input**: Ý tưởng task hoặc folder task đang dựng.
- **Output**: Regular task scaffold hoặc audit checklist.
- **Mục tiêu**:
  - Đảm bảo cấu trúc task đúng Platform Submission Guide.
  - Kiểm tra `instruction.md`, `task.toml`, Dockerfile, oracle, verifier.
  - Đảm bảo task không copy `tests/` hoặc `solution/` vào image.
- **Khi nào dùng**: Khi dựng task mới hoặc cần audit cấu trúc trước khi chạy Harbor.

---

### 4) Issue To Regression Test

- **Slash command gợi ý**: `/issue-to-regression-test`
- **Input**: Issue/PR đã chọn và hành vi cần reproduce.
- **Output**: Thiết kế verifier tests cho `tests/test_outputs.py`.
- **Mục tiêu**:
  - Tạo direct regression reproducer.
  - Thêm boundary/ordering case.
  - Thêm normal behavior preservation.
  - Thêm anti-shortcut case.
  - Đảm bảo mọi behavior trong tests đều có trong `instruction.md`.
- **Khi nào dùng**: Sau khi đã chọn bug upstream, trước khi viết verifier.

---

### 5) Terminus Hard Python Verifier

- **Slash command gợi ý**: `/terminus-hard-python-verifier`
- **Input**: Task Python debugging và các behavior cần kiểm tra.
- **Output**: Verifier pattern, `tests/test.sh`, `tests/test_outputs.py`, oracle guidance.
- **Mục tiêu**:
  - Viết verifier đủ mạnh cho Python Hard task.
  - Test qua subprocess hoặc public API.
  - Parse JSON/XML/CSV bằng parser thật.
  - Tránh test source-code shape.
- **Khi nào dùng**: Khi task là Python và cần đảm bảo agent không pass bằng shortcut.

---

### 6) Upstream Repo Sanitizer

- **Slash command gợi ý**: `/upstream-repo-sanitizer`
- **Input**: Folder task có `environment/repo`.
- **Output**: Repo đã được prune/sanitize hoặc báo cáo cần sửa.
- **Mục tiêu**:
  - Giữ `environment/ <= 100 MiB`.
  - Không có file đơn lẻ quá `50 MiB`.
  - Xóa `.git/`, cache, macOS junk, secret-shaped files.
  - Thêm `.dockerignore`.
  - Thêm `pyproject.toml` ruff exclude nếu cần.
- **Khi nào dùng**: Trước khi build Docker hoặc chạy Harbor.

---

### 7) Task Harbor Runner

- **Slash command gợi ý**: `/task-harbor-runner`
- **Input**: Folder task.
- **Output**: Kết quả oracle/nop/CI/agent run và hướng triage.
- **Mục tiêu**:
  - Chạy `harbor run -a oracle`.
  - Chạy `harbor run -a nop`.
  - Chạy `harbor tasks check`.
  - Đọc log lỗi và follow feedback cụ thể.
- **Khi nào dùng**: Sau khi task đã có đủ files và muốn validate.

Các lệnh chính:

```bash
harbor run -a oracle -p <task-folder>
harbor run -a nop -p <task-folder>
harbor tasks check -m openai/@openai/gpt-5.2 <task-folder>
```

Nếu lệnh có option output, ghi report vào `workspace/reports/`.

---

### 8) Task Zip Submit

- **Slash command gợi ý**: `/task-zip-submit`
- **Input**: Folder task đã pass validation.
- **Output**: ZIP sạch để upload lên Snorkel Platform.
- **Mục tiêu**:
  - Zip contents của task folder, không zip folder cha.
  - Chỉ include allowlist submission: `instruction.md`, `task.toml`, `pyproject.toml` nếu cần, `environment/`, `solution/`, `tests/`.
  - Loại `.DS_Store`, `._*`, `__MACOSX`, `__pycache__`, `*.pyc`.
  - Verify archive không bị lồng folder.

Từ trong task root:

```bash
find . \( -name '.DS_Store' -o -name '._*' -o -name '__pycache__' \) -exec rm -rf {} +

TASK_NAME="$(basename "$PWD")"
mkdir -p ../submissions
zip -rX "../submissions/${TASK_NAME}.zip" instruction.md task.toml pyproject.toml environment solution tests \
    -x '*.DS_Store' -x '__MACOSX/*' -x '*/__pycache__/*' -x '*.pyc'
```

Nếu không có `pyproject.toml`, bỏ nó khỏi command.

Không include `workspace/`, `reports/`, `submissions/`, logs, cache, scratch notes, hoặc folder cha của task.

Verify:

```bash
TASK_NAME="$(basename "$PWD")"
unzip -l "../submissions/${TASK_NAME}.zip" | head -40
unzip -l "../submissions/${TASK_NAME}.zip" | grep -E '__MACOSX|\.DS_Store|/\._|__pycache__|\.pyc|reports/|submissions/|workspace/' || true
```

---

## Lưu ý chung

- Task clone, report và ZIP sinh ra nằm trong `workspace/` và bị `.gitignore`, không đẩy lên git.
- Mỗi skill có file mô tả chi tiết trong `skills/{tên-kỹ-năng}/SKILL.md`.
- `instruction.md` phải là human language, không phải LLM checklist.
- Với Docker/Harbor/CI, luôn đọc feedback cụ thể trước khi đoán lỗi.
- Oracle pass chưa đủ; nop phải fail.
- Python task nên target `hard`. Nếu real agents pass quá dễ, task có khả năng bị reject.
- ZIP phải chứa files trực tiếp ở root, không lồng thêm folder task.

---

## Checklist trước khi nói task ready

- [ ] Folder name đúng dạng `tbrain-<problem-slug>`, không có domain filler.
- [ ] `instruction.md` nghe như human bug report, không như LLM checklist.
- [ ] `task.toml` parse được, có `allow_internet = false`.
- [ ] Dockerfile digest-pinned, có `tmux` và `asciinema`.
- [ ] `environment/` <= 100 MiB, mỗi file <= 50 MiB.
- [ ] Không copy `tests/` hoặc `solution/` vào image.
- [ ] Oracle pass.
- [ ] Nop fail.
- [ ] Tests có docstring và test behavior.
- [ ] Tests map với instruction.
- [ ] ZIP không lồng folder, không có macOS junk.
