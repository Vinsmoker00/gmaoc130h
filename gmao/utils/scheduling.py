"""Utility helpers for scheduling and critical path calculations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence


@dataclass
class ScheduledTask:
    """Computed schedule for a task.

    Attributes
    ----------
    id:
        Identifier of the task in the original data source.
    start:
        Earliest possible start time expressed in hours from the project origin.
    finish:
        Earliest possible finish time expressed in hours from the project origin.
    duration:
        Duration of the task in hours.
    """

    id: int
    start: float
    finish: float
    duration: float


class CyclicDependencyError(ValueError):
    """Raised when the provided dependency graph contains a cycle."""


def _normalise_tasks(tasks: Sequence[dict]) -> List[dict]:
    normalised: List[dict] = []
    for index, task in enumerate(tasks):
        duration = float(task.get("duration", 0) or 0)
        if duration < 0:
            duration = 0.0
        normalised.append(
            {
                "id": int(task["id"]),
                "duration": duration,
                "dependencies": list({int(dep) for dep in task.get("dependencies", []) if dep is not None}),
                "order": task.get("order", index),
            }
        )
    return normalised


def _inject_sequential_dependencies(tasks: List[dict]) -> None:
    if len(tasks) < 2:
        return
    if all(len(task["dependencies"]) == 0 for task in tasks):
        tasks.sort(key=lambda task: (task["order"], task["id"]))
        previous_id = None
        for task in tasks:
            if previous_id is not None:
                task["dependencies"].append(previous_id)
            previous_id = task["id"]


def _topological_order(tasks: Sequence[dict]) -> List[int]:
    indegree: Dict[int, int] = {}
    adjacency: Dict[int, List[int]] = {}
    for task in tasks:
        task_id = task["id"]
        indegree.setdefault(task_id, 0)
        adjacency.setdefault(task_id, [])
    for task in tasks:
        for dep in task["dependencies"]:
            indegree[task["id"]] = indegree.get(task["id"], 0) + 1
            adjacency.setdefault(dep, []).append(task["id"])
    queue = [task_id for task_id, degree in indegree.items() if degree == 0]
    order: List[int] = []
    while queue:
        current = queue.pop(0)
        order.append(current)
        for neighbour in adjacency.get(current, []):
            indegree[neighbour] -= 1
            if indegree[neighbour] == 0:
                queue.append(neighbour)
    if len(order) != len(tasks):
        raise CyclicDependencyError("Task dependencies contain a cycle")
    return order


def compute_critical_path(tasks: Sequence[dict]) -> dict:
    """Compute the critical path for a collection of tasks.

    Parameters
    ----------
    tasks:
        Iterable of dictionaries describing each task. The minimal keys are
        ``id`` and ``duration`` (in hours). ``dependencies`` may optionally be
        provided as an iterable of task identifiers. When dependencies are not
        provided, tasks are assumed to be sequential following their ``order``
        attribute or the iteration order.

    Returns
    -------
    dict
        ``{"project_duration": float, "critical_path": list[int], "tasks": list[ScheduledTask]}``
    """

    if not tasks:
        return {"project_duration": 0.0, "critical_path": [], "tasks": []}

    normalised = _normalise_tasks(tasks)
    _inject_sequential_dependencies(normalised)

    task_map = {task["id"]: task for task in normalised}
    order = _topological_order(normalised)

    earliest_start: Dict[int, float] = {}
    earliest_finish: Dict[int, float] = {}
    predecessor: Dict[int, int | None] = {}

    for task_id in order:
        task = task_map[task_id]
        dependencies = task["dependencies"]
        if dependencies:
            pred = max(dependencies, key=lambda dep_id: earliest_finish.get(dep_id, 0.0))
            start = earliest_finish.get(pred, 0.0)
            predecessor[task_id] = pred
        else:
            start = 0.0
            predecessor[task_id] = None
        finish = start + task["duration"]
        earliest_start[task_id] = start
        earliest_finish[task_id] = finish

    if earliest_finish:
        final_task = max(order, key=lambda tid: earliest_finish.get(tid, 0.0))
        project_duration = earliest_finish[final_task]
    else:
        final_task = None
        project_duration = 0.0

    critical_path: List[int] = []
    cursor = final_task
    while cursor is not None:
        critical_path.append(cursor)
        cursor = predecessor.get(cursor)
    critical_path.reverse()

    scheduled_tasks = [
        ScheduledTask(id=task_id, start=earliest_start[task_id], finish=earliest_finish[task_id], duration=task_map[task_id]["duration"])
        for task_id in order
    ]

    return {
        "project_duration": project_duration,
        "critical_path": critical_path,
        "tasks": scheduled_tasks,
    }

