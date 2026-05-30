# Terminus_Task_Skill

Bộ kỹ năng hỗ trợ tạo Terminus Regular task từ issue/PR upstream đã đóng hoặc đã merge. Bộ này tập trung vào quy trình clone bug thật thành task `tbrain-*`, viết prompt tự nhiên như người thật, thiết kế verifier đủ chặt, validate bằng Harbor, và đóng gói ZIP đúng chuẩn Snorkel Platform.

---

> **Disclaimer**: Đây là bộ workflow cá nhân để tạo và kiểm tra task Terminus. Nội dung được tổng hợp từ tài liệu local trong `docs/`, task mẫu, và kinh nghiệm debug CI/Harbor. Nếu rule trong Snorkel Platform thay đổi, ưu tiên feedback mới nhất từ CI/Harbor/LLMaJ.

---

## Tổng quan

Repo này cung cấp các skill để tạo task end to end:

| # | Tên kỹ năng | Slash command gợi ý | Mô tả |
|---|---|---|---|
| 1 | **Task Clone** | `/task-clone` | Clone một closed issue/PR upstream thành Terminus Regular task trong `workspace/tbrain-<problem-slug>` |
| 2 | **Task Miner** | `/task-miner` | Mine issue/PR tốt từ repo source bất kỳ, ví dụ `dagster-io/dagster`, để làm task Hard |
| 3 | **Pytest Closed Issue Task Miner** | `/pytest-closed-issue-task-miner` | Tìm issue/PR tốt từ `pytest-dev/pytest` để làm task Hard |
| 4 | **Terminus Regular Task Authoring** | `/terminus-regular-task-authoring` | Tạo/audit cấu trúc Regular task theo Platform Submission Guide |
| 5 | **Issue To Regression Test** | `/issue-to-regression-test` | Biến issue/PR thành verifier tests hành vi, có regression và anti-shortcut |
| 6 | **Terminus Hard Python Verifier** | `/terminus-hard-python-verifier` | Viết verifier/oracle cho Python debugging task đủ khó |
| 7 | **Upstream Repo Sanitizer** | `/upstream-repo-sanitizer` | Làm sạch `environment/repo`, giữ build context dưới giới hạn CI |
| 8 | **Task Harbor Runner** | `/task-harbor-runner` | Chạy và debug Harbor: oracle, nop, CI checks, real agents |
| 9 | **Task Zip Submit** | `/task-zip-submit` | Đóng gói ZIP sạch, đúng cấu trúc, không dính macOS junk |

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
|   |-- pytest-closed-issue-task-miner/SKILL.md
|   |-- terminus-regular-task-authoring/SKILL.md
|   |-- issue-to-regression-test/SKILL.md
|   |-- terminus-hard-python-verifier/SKILL.md
|   |-- upstream-repo-sanitizer/SKILL.md
|   |-- task-harbor-runner/SKILL.md
|   `-- task-zip-submit/SKILL.md
|-- .codex/skills/                # Bản sync cho Codex trong workspace
|-- .claude/skills/               # Bản sync cho Claude trong workspace
`-- workspace/                    # Task, reports, ZIP local; bị .gitignore
    |-- tbrain-*/
    |-- reports/
    `-- submissions/
```

Task clone, Harbor reports và submission ZIP đều để trong `workspace/`. Đây là khu vực local, không đẩy lên git. `.gitignore` đã ignore nguyên thư mục `/workspace/`.

---

## Quy trình làm việc (Workflow)

Các skill được thiết kế để phối hợp theo thứ tự sau:

```text
task-miner                         [tùy chọn, nếu cần tìm issue/PR từ repo bất kỳ]
        ↓
pytest-closed-issue-task-miner     [tùy chọn, nếu repo là pytest-dev/pytest]
        ↓
task-clone
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

**NOTE**: Nếu đã có issue/PR URL cụ thể, có thể bắt đầu từ `task-clone`. Nếu cần mine từ repo bất kỳ, dùng `task-miner`; nếu repo là `pytest-dev/pytest`, có thể dùng thêm `pytest-closed-issue-task-miner` để tận dụng heuristic riêng cho pytest.

### Thứ tự triển khai

1. **task-miner** *(tùy chọn)*: Quét closed issue/PR từ repo source bất kỳ, lọc bug đủ khó, tránh docs-only hoặc fix quá dễ.
2. **pytest-closed-issue-task-miner** *(tùy chọn)*: Quét closed issue/PR từ `pytest-dev/pytest`, lọc bug theo heuristic riêng của pytest internals.
3. **task-clone**: Xác định bug, commit trước fix, tên task `workspace/tbrain-<problem-slug>`, và skeleton Regular task.
4. **upstream-repo-sanitizer**: Clone/stage repo vào `environment/repo`, prune file nặng, xóa file giống secret, kiểm tra `environment/ <= 100 MiB`.
5. **issue-to-regression-test**: Chuyển bug upstream thành verifier tests: direct regression, boundary, normal behavior, anti-shortcut.
6. **terminus-hard-python-verifier**: Hoàn thiện `tests/test_outputs.py`, `tests/test.sh`, oracle pattern và coverage cho Python Hard task.
7. **terminus-regular-task-authoring**: Audit `instruction.md`, `task.toml`, Dockerfile, oracle và verifier theo Platform Submission Guide.
8. **task-harbor-runner**: Chạy `harbor run -a oracle`, `harbor run -a nop`, `harbor tasks check`, rồi follow feedback nếu fail.
9. **task-zip-submit**: Dọn cache/macOS junk, zip đúng contents của task folder, verify archive trước khi upload.

### Phối hợp giữa các kỹ năng

- **task-clone** là skill điều phối chính. Khi người dùng nói "clone task từ issue/PR này", bắt đầu từ đây.
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

### 5) Quy tắc Harbor feedback

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
- **Input**: GitHub issue URL, PR URL, `owner/repo`, hoặc mô tả task muốn clone.
- **Output**: Folder `workspace/tbrain-<problem-slug>/`.
- **Mục tiêu**:
  - Biến một bug upstream thật thành Terminus Regular task.
  - Chọn commit trước fix để stage vào `environment/repo`.
  - Đặt tên task đúng dạng `tbrain-<problem-slug>`.
  - Không đưa tên repo/tool vào task name nếu không cần.
  - Tạo layout chuẩn gồm `instruction.md`, `task.toml`, `environment/`, `solution/`, `tests/`.
- **Khi nào dùng**: Khi bắt đầu clone một task mới từ issue/PR thật.

---

### 2) Task Miner

- **Slash command gợi ý**: `/task-miner`
- **Input**: Repo source dạng `owner/repo`, GitHub repo URL, `/issues`, `/pulls`, issue URL hoặc PR URL.
- **Output**: Danh sách candidate issue/PR có thể làm task Hard, kèm commit trước fix và kế hoạch verifier.
- **Mục tiêu**:
  - Tìm bug upstream thật từ repo bất kỳ, ví dụ `https://github.com/dagster-io/dagster/pulls`.
  - Ưu tiên issue/PR đã đóng/merge có test regression và reproduce offline được.
  - Loại docs-only, typo-only, dependency bump, CI-only, release metadata, typing-only.
  - Chuẩn bị candidate đủ rõ để chuyển sang `task-clone`.
- **Khi nào dùng**: Khi chưa có issue/PR cụ thể hoặc muốn mine từ repo không phải `pytest-dev/pytest`.

---

### 3) Pytest Closed Issue Task Miner

- **Slash command gợi ý**: `/pytest-closed-issue-task-miner`
- **Input**: Repo `pytest-dev/pytest` hoặc issue/PR trong repo này.
- **Output**: Danh sách candidate issue/PR có thể làm task Hard.
- **Mục tiêu**:
  - Tìm bug trong pytest internals đủ khó.
  - Ưu tiên fixture lifecycle, reporting, collection, assertion rewriting, JUnit XML, plugin hooks.
  - Loại docs-only, typo-only, dependency bump, CI-only.
- **Khi nào dùng**: Khi chưa có issue/PR cụ thể và muốn mine domain pytest.

---

### 4) Terminus Regular Task Authoring

- **Slash command gợi ý**: `/terminus-regular-task-authoring`
- **Input**: Ý tưởng task hoặc folder task đang dựng.
- **Output**: Regular task scaffold hoặc audit checklist.
- **Mục tiêu**:
  - Đảm bảo cấu trúc task đúng Platform Submission Guide.
  - Kiểm tra `instruction.md`, `task.toml`, Dockerfile, oracle, verifier.
  - Đảm bảo task không copy `tests/` hoặc `solution/` vào image.
- **Khi nào dùng**: Khi dựng task mới hoặc cần audit cấu trúc trước khi chạy Harbor.

---

### 5) Issue To Regression Test

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

### 6) Terminus Hard Python Verifier

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

### 7) Upstream Repo Sanitizer

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

### 8) Task Harbor Runner

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

### 9) Task Zip Submit

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
