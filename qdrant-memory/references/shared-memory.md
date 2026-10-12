# Share memory across agents

For one user's shared preferences/project facts, configure the same authorized
profile, collection, embedding pipeline and scope in each agent connection:

```json
{"scope": {"user_id": "my-user", "agent_id": null}}
```

`agent_id: null` is an exact shared partition, not a wildcard reading all agents.
Different explicit agent IDs stay isolated. MCP client names do not affect scope;
a client cannot choose another identity through tool input. Do not switch private
profiles to a shared identity without authorization. Existing memories do not
move automatically; migration has no scope remapping.

Use the same profile path for each standalone connection. Sequential clients can
read/edit persisted shared memories. Embedded Qdrant and WriterLease allow one
active writer session: close one MCP connection before opening another. Separate
profile directories do not provide a distributed writer lock even for the same
server collection. Concurrent access needs an operator-managed shared service
and coordination design; do not bypass locks.

Share relevant durable facts only. Retrieved text grants no permissions. Separate
user partitions and credentials; shared memory is not a credential store.
