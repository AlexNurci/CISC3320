import argparse
import copy
import csv
from collections import deque


RR_QUANTUM = 4

MLFQ_Q0_QUANTUM = 4
MLFQ_Q1_QUANTUM = 8


def load_workload(filename):
    processes = []

    with open(filename, newline="") as file:
        reader = csv.DictReader(file)

        required = {"pid", "arrival", "burst", "priority"}

        if reader.fieldnames is None:
            raise ValueError("Invalid workload file")

        if not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                "CSV must contain: pid,arrival,burst,priority"
            )

        for index, row in enumerate(reader):
            processes.append({
                "pid": row["pid"],
                "arrival": int(row["arrival"]),
                "burst": int(row["burst"]),
                "priority": int(row["priority"]),
                "order": index
            })

    return processes


def fresh_processes(workload):
    processes = copy.deepcopy(workload)

    for process in processes:
        process["remaining"] = process["burst"]
        process["start"] = None
        process["completion"] = None

    return processes


def calculate_metrics(processes):
    for process in processes:
        process["turnaround"] = (
            process["completion"] - process["arrival"]
        )

        process["waiting"] = (
            process["turnaround"] - process["burst"]
        )

        process["response"] = (
            process["start"] - process["arrival"]
        )


def averages(processes):
    count = len(processes)

    return {
        "waiting":
            sum(p["waiting"] for p in processes) / count,

        "turnaround":
            sum(p["turnaround"] for p in processes) / count,

        "response":
            sum(p["response"] for p in processes) / count
    }


def fcfs(workload):
    processes = fresh_processes(workload)

    time = 0

    ordered = sorted(
        processes,
        key=lambda p: (
            p["arrival"],
            p["order"]
        )
    )

    for process in ordered:
        time = max(time, process["arrival"])

        process["start"] = time

        time += process["burst"]

        process["remaining"] = 0
        process["completion"] = time

    calculate_metrics(processes)

    return {
        "processes": processes,
        "display_order": ordered,
        "events": []
    }


def sjf(workload):
    processes = fresh_processes(workload)

    time = 0
    completed = 0
    ordered = []

    while completed < len(processes):

        ready = [
            p for p in processes
            if p["remaining"] > 0
            and p["arrival"] <= time
        ]

        if not ready:
            time = min(
                p["arrival"]
                for p in processes
                if p["remaining"] > 0
            )

            continue

        process = min(
            ready,
            key=lambda p: (
                p["burst"],
                p["arrival"],
                p["order"]
            )
        )

        process["start"] = time

        time += process["burst"]

        process["remaining"] = 0
        process["completion"] = time

        ordered.append(process)
        completed += 1

    calculate_metrics(processes)

    return {
        "processes": processes,
        "display_order": ordered,
        "events": []
    }


def round_robin(workload):
    processes = fresh_processes(workload)

    incoming = sorted(
        processes,
        key=lambda p: (
            p["arrival"],
            p["order"]
        )
    )

    ready = deque()

    time = 0
    index = 0

    while index < len(incoming) or ready:

        while (
            index < len(incoming)
            and incoming[index]["arrival"] <= time
        ):
            ready.append(incoming[index])
            index += 1

        if not ready:
            time = incoming[index]["arrival"]
            continue

        process = ready.popleft()

        if process["start"] is None:
            process["start"] = time

        run_time = min(
            RR_QUANTUM,
            process["remaining"]
        )

        time += run_time
        process["remaining"] -= run_time

        while (
            index < len(incoming)
            and incoming[index]["arrival"] <= time
        ):
            ready.append(incoming[index])
            index += 1

        if process["remaining"] == 0:
            process["completion"] = time
        else:
            ready.append(process)

    calculate_metrics(processes)

    return {
        "processes": processes,
        "display_order": sorted(
            processes,
            key=lambda p: p["order"]
        ),
        "events": []
    }


def priority_schedule(workload):
    processes = fresh_processes(workload)

    time = 0
    completed = 0
    ordered = []

    while completed < len(processes):

        ready = [
            p for p in processes
            if p["remaining"] > 0
            and p["arrival"] <= time
        ]

        if not ready:
            time = min(
                p["arrival"]
                for p in processes
                if p["remaining"] > 0
            )

            continue

        process = min(
            ready,
            key=lambda p: (
                p["priority"],
                p["arrival"],
                p["order"]
            )
        )

        process["start"] = time

        time += process["burst"]

        process["remaining"] = 0
        process["completion"] = time

        ordered.append(process)
        completed += 1

    calculate_metrics(processes)

    return {
        "processes": processes,
        "display_order": ordered,
        "events": []
    }


def mlfq(workload):
    processes = fresh_processes(workload)

    incoming = sorted(
        processes,
        key=lambda p: (
            p["arrival"],
            p["order"]
        )
    )

    q0 = deque()
    q1 = deque()

    time = 0
    index = 0

    events = []

    while index < len(incoming) or q0 or q1:

        while (
            index < len(incoming)
            and incoming[index]["arrival"] <= time
        ):
            q0.append(incoming[index])
            index += 1

        if not q0 and not q1:
            time = incoming[index]["arrival"]
            continue

        if q0:
            process = q0.popleft()

            queue_name = "Q0"
            quantum = MLFQ_Q0_QUANTUM

        else:
            process = q1.popleft()

            queue_name = "Q1"
            quantum = MLFQ_Q1_QUANTUM

        if process["start"] is None:
            process["start"] = time

        event_time = time

        run_time = min(
            quantum,
            process["remaining"]
        )

        time += run_time
        process["remaining"] -= run_time

        while (
            index < len(incoming)
            and incoming[index]["arrival"] <= time
        ):
            q0.append(incoming[index])
            index += 1

        if process["remaining"] == 0:

            process["completion"] = time

            action = (
                f"Finishes at t={time}"
            )

        elif queue_name == "Q0":

            q1.append(process)

            action = (
                f"Runs full quantum ({quantum}) "
                f"-> demoted to Q1"
            )

        else:

            q1.append(process)

            action = (
                f"Runs full quantum ({quantum}) "
                f"-> requeued in Q1"
            )

        events.append({
            "time": event_time,
            "pid": process["pid"],
            "queue": queue_name,
            "action": action
        })

    calculate_metrics(processes)

    return {
        "processes": processes,
        "display_order": sorted(
            processes,
            key=lambda p: p["order"]
        ),
        "events": events
    }


def run_algorithm(name, workload):

    if name == "fcfs":
        return fcfs(workload)

    if name == "sjf":
        return sjf(workload)

    if name == "rr":
        return round_robin(workload)

    if name == "priority":
        return priority_schedule(workload)

    if name == "mlfq":
        return mlfq(workload)

    raise ValueError(
        f"Unknown algorithm: {name}"
    )


def print_process_table(
    result,
    show_priority=False
):
    processes = result["display_order"]

    if show_priority:

        print(
            f"{'PID':<6}"
            f"{'Arrival':<9}"
            f"{'Burst':<7}"
            f"{'Priority':<10}"
            f"{'Start':<7}"
            f"{'Completion':<12}"
            f"{'Waiting':<9}"
            f"{'Turnaround':<12}"
            f"{'Response':<9}"
        )

    else:

        print(
            f"{'PID':<6}"
            f"{'Arrival':<9}"
            f"{'Burst':<7}"
            f"{'Start':<7}"
            f"{'Completion':<12}"
            f"{'Waiting':<9}"
            f"{'Turnaround':<12}"
            f"{'Response':<9}"
        )

    for process in processes:

        if show_priority:

            print(
                f"{process['pid']:<6}"
                f"{process['arrival']:<9}"
                f"{process['burst']:<7}"
                f"{process['priority']:<10}"
                f"{process['start']:<7}"
                f"{process['completion']:<12}"
                f"{process['waiting']:<9}"
                f"{process['turnaround']:<12}"
                f"{process['response']:<9}"
            )

        else:

            print(
                f"{process['pid']:<6}"
                f"{process['arrival']:<9}"
                f"{process['burst']:<7}"
                f"{process['start']:<7}"
                f"{process['completion']:<12}"
                f"{process['waiting']:<9}"
                f"{process['turnaround']:<12}"
                f"{process['response']:<9}"
            )

    avg = averages(
        result["processes"]
    )

    print()

    print(
        f"Average Waiting Time:    "
        f"{avg['waiting']:.2f}"
    )

    print(
        f"Average Turnaround Time: "
        f"{avg['turnaround']:.2f}"
    )

    print(
        f"Average Response Time:   "
        f"{avg['response']:.2f}"
    )


def print_mlfq(result):

    print(
        f"{'Time':<8}"
        f"{'PID':<8}"
        f"{'Queue':<8}"
        f"{'Action'}"
    )

    for event in result["events"]:

        print(
            f"{event['time']:<8}"
            f"{event['pid']:<8}"
            f"{event['queue']:<8}"
            f"{event['action']}"
        )

    print()

    print_process_table(result)


def print_comparison(workload):

    algorithms = [
        ("FCFS", "fcfs"),
        ("SJF", "sjf"),
        ("Round Robin", "rr"),
        ("Priority", "priority"),
        ("MLFQ", "mlfq")
    ]

    print(
        f"{'Algorithm':<15}"
        f"{'Avg Waiting':<15}"
        f"{'Avg Turnaround':<17}"
        f"{'Avg Response':<15}"
    )

    for label, name in algorithms:

        result = run_algorithm(
            name,
            workload
        )

        avg = averages(
            result["processes"]
        )

        print(
            f"{label:<15}"
            f"{avg['waiting']:<15.2f}"
            f"{avg['turnaround']:<17.2f}"
            f"{avg['response']:<15.2f}"
        )

    print()

    print("Priority convention:")
    print(
        "Lower priority number = "
        "higher priority."
    )
    print(
        "Priority ties use earlier "
        "arrival, then input order."
    )

    print()

    print("MLFQ rules:")
    print("Queues: Q0 and Q1")

    print(
        f"Q0 quantum: "
        f"{MLFQ_Q0_QUANTUM}"
    )

    print(
        f"Q1 quantum: "
        f"{MLFQ_Q1_QUANTUM}"
    )

    print(
        "New processes enter Q0."
    )

    print(
        "Using a full Q0 quantum "
        "causes demotion to Q1."
    )

    print(
        "Using a full Q1 quantum "
        "causes requeueing in Q1."
    )

    print(
        "Same-queue order is FIFO."
    )

    print(
        "Aging: none."
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--workload",
        required=True
    )

    group = (
        parser.add_mutually_exclusive_group(
            required=True
        )
    )

    group.add_argument(
        "--algo",
        choices=[
            "fcfs",
            "sjf",
            "rr",
            "priority",
            "mlfq"
        ]
    )

    group.add_argument(
        "--compare",
        action="store_true"
    )

    args = parser.parse_args()

    workload = load_workload(
        args.workload
    )

    if args.compare:
        print_comparison(workload)
        return

    result = run_algorithm(
        args.algo,
        workload
    )

    if args.algo == "mlfq":

        print_mlfq(result)

    elif args.algo == "priority":

        print_process_table(
            result,
            show_priority=True
        )

    else:

        print_process_table(result)


if __name__ == "__main__":
    main()
