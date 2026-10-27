# Project Context

In src/users.js, getData(api) calls api.listUsers(), and activeUsers(api)
obtains the list and filters users by user.active. src/settings.json contains
pageSize: 50 and cacheTtlSeconds: 60. src/examples.txt is empty.

In the earlier pagination discussion, we chose a cursor ordered by createdAt and
id, with 50 records per request. The server returns nextCursor; nextCursor is
absent on the last page. Later, we discussed caching API responses for 60
seconds.

This project's configured persistent instruction memory is
memory/instructions.md. It is isolated experimental memory, not the user's
global memory. Preserve existing instructions when updating it.
