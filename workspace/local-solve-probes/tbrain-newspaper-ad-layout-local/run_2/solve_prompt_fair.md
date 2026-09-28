You are solving a Terminus task. Your working directory is /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3/workspace/local-solve-probes/tbrain-newspaper-ad-layout-local/run_2/solve . Work only inside it: do not read any parent or sibling directory, and do not search for solutions, tests, rubrics, reports or earlier attempts. This is a one-shot attempt; you will get no feedback afterwards.

Read `instruction.md` first. In this copy, the task's `/app` is the folder `environment/app` (so `/app/layouts/` is `environment/app/layouts/`).

The real task runs in a Docker container with 2 CPUs, no network and only Python 3.13 and its standard library. Run every computation (your scripts, any search, the checker) inside that same container with this command, from your working directory:

    docker run --rm --cpus 2 --network none -v "$PWD/environment/app:/app" -w /app preflight-agent-tbrain-newspaper-ad-layout:latest python3 <your script and arguments>

Put your own scripts under `environment/app/` so the container sees them. Do not run Python or any search on the host, and do not start more than one such container at a time. `docker run -d` for a long job is fine, still one container at a time; check on it with `docker logs`.

Hard time limit: the attempt ends at 09:56 local time (check with the date command) (90 minutes from the start). Whatever files are in `environment/app/layouts/` at that moment are graded, so keep a valid file there for each instance at all times and overwrite it whenever you find a better one. Stop all containers you started before the deadline.

When done, reply briefly: the files you wrote, the checker's result for each, and how you searched.
