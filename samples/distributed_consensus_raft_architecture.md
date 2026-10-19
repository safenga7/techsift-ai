# Distributed Consensus: Architectural Overview of the Raft Algorithm

## Abstract

Distributed consensus is a fundamental primitive in fault-tolerant distributed systems. It guarantees that a cluster of computing nodes can reach an agreement on state transitions even in the presence of network partitions, hardware failures, and packet delays. The Raft consensus algorithm was designed specifically to prioritize understandability while offering the same operational safety and performance characteristics as Multi-Paxos.

---

## 1. Core Principles and Node States

In a Raft cluster, every node exists in one of three mutually exclusive states:
1. **Leader**: Handles all incoming client requests, manages log replication across follower nodes, and sends periodic heartbeats to maintain cluster authority.
2. **Follower**: Completely passive; responds to remote procedure calls (RPCs) issued by leaders and candidate nodes without initiating communication.
3. **Candidate**: An active state assumed when a follower detects a leader election timeout, used to collect votes from cluster peers.

Time in Raft is partitioned into arbitrary **terms**. Each term is identified by a monotonically increasing integer. Terms act as a logical clock, allowing nodes to detect obsolete information such as stale leaders.

```text
+--------------+     Timeout / Starts Election     +---------------+
|   Follower   | --------------------------------> |   Candidate   |
+--------------+                                   +---------------+
       ^                                                   |
       |             Discovers Current Leader              |  Receives Majority Votes
       |              or Higher Election Term              |
       +---------------------------------------------------+
       ^                                                   |
       |                                                   v
       |             Discovers Higher Term         +---------------+
       +------------------------------------------ |    Leader     |
                                                   +---------------+
```

---

## 2. Leader Election Protocol

Leader election operates via randomized timers to prevent split-vote scenarios:
- **Heartbeat Interval**: The leader broadcasts empty `AppendEntries` RPCs at regular intervals (typically 50ms).
- **Election Timeout**: Followers maintain an election timer randomized between 150ms and 300ms.
- If a follower receives no heartbeat before its timer expires, it increments its term, transitions to candidate state, votes for itself, and broadcasts `RequestVote` RPCs to all peers.
- A candidate wins the election if it receives affirmative votes from a strict majority ($N/2 + 1$) of nodes in the cluster.

---

## 3. Log Replication & Commit Index

Once a leader is established, client operations flow through a strict two-phase commit sequence:
1. **Log Entry Append**: The leader appends the proposed command to its local log as an uncommitted entry.
2. **Replication Broadcast**: The leader sends `AppendEntries` RPCs containing the new entry to all follower nodes.
3. **Majority Acknowledgment**: When a majority of followers safely persist the entry to disk, the leader increments its `commitIndex`.
4. **State Machine Execution**: The leader applies the entry to its state machine and returns the result to the calling client.
5. **Follower Execution**: On subsequent heartbeats, followers are informed of the updated `commitIndex` and apply matching entries to their local state machines.

---

## 4. Safety Invariants & Boundary Conditions

To guarantee deterministic linearizability, Raft enforces five invariant safety rules:

* **Election Safety**: At most one leader can be elected in a given term.
* **Leader Append-Only**: A leader never overwrites or truncates its own log entries; it only appends new entries.
* **Log Matching Property**: If two distinct logs contain an entry with the same index and term, they are identical up to that index.
* **Leader Completeness**: If a log entry is committed in a given term, that entry will be present in the logs of the leaders for all higher-numbered terms.
* **State Machine Safety**: If a server has applied a log entry at a given index to its state machine, no other server will ever apply a different log entry for the same index.

---

## 5. Architectural Trade-Offs

| Dimension | Raft Characteristics |
| :--- | :--- |
| **Fault Tolerance** | Tolerates up to $f$ failures in a cluster of $2f + 1$ nodes. |
| **Network Partition Behavior** | Minority partitions cannot commit entries, preserving consistency (CP system under CAP theorem). |
| **Throughput Bottleneck** | Centralized leader must process all log entries; mitigated by pipelining and batching. |
| **Failure Recovery** | Fast recovery via follower log synchronization without complex multi-phase consensus reconfiguration. |
