export async function getData(api) {
  return api.listUsers();
}

export async function activeUsers(api) {
  const users = await getData(api);
  return users.filter(user => user.active);
}
