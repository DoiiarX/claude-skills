# Metric definitions

## Application boundary

The profiler starts the command itself and follows descendants discovered through parent-child relationships. Unrelated system processes are excluded. Descendants that detach remain included after discovery until they exit.

## Reported metrics

- `wall_time_s`: elapsed monotonic time from process launch until the root and discovered descendants finish.
- `cpu_user_s`, `cpu_system_s`, `cpu_total_s`: last observed cumulative CPU time summed across unique `(PID, creation time)` identities.
- `average_cpu_percent_core_scale`: `cpu_total_s / wall_time_s * 100`. One fully busy logical CPU is 100%.
- `average_cpu_percent_machine`: core-scale percentage divided by the logical CPU count. A fully busy machine is 100%.
- `peak_rss_bytes`: maximum sampled sum of resident memory for concurrently alive observed processes.
- `peak_vms_bytes`: maximum sampled sum of virtual memory for concurrently alive observed processes.
- `io_read_bytes`, `io_write_bytes`: last observed cumulative process I/O counters summed across observed process identities where the OS exposes them.
- `process_count_seen`: number of unique process identities observed during the run.

## Accuracy boundaries

This is a sampled process-tree profiler. A process that is created and exits entirely between samples may be missed, so its CPU, memory, and I/O can be undercounted. Lower the interval for short-lived worker processes.

For enforcement-grade accounting use an OS containment backend:

- Windows: Job Objects with accounting queries.
- Linux: cgroup v2, optionally combined with `perf stat`.
- macOS: process groups plus Mach or `proc_pidinfo` APIs.

Do not compare memory semantics across operating systems without noting that RSS and virtual-memory accounting differ. Run benchmarks on an otherwise stable machine, use warmups, repeat measurements, and record the environment.
