self.addEventListener('push', (event) => {
  let payload = {};
  try {
    payload = event.data?.json() || {};
  } catch {
    payload = { body: event.data?.text() || '' };
  }

  const title = payload.title || 'Badminton Court Control Panel';
  const targetUrl = new URL(payload.url || '/', self.location.origin);
  if (targetUrl.origin !== self.location.origin) {
    targetUrl.href = self.location.origin;
  }

  event.waitUntil(self.registration.showNotification(title, {
    body: payload.body || '',
    icon: payload.icon || '/static/shuttlecock.png',
    badge: '/static/shuttlecock.png',
    tag: payload.tag || 'court-update',
    renotify: true,
    data: { url: targetUrl.href },
  }));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = new URL(
    event.notification.data?.url || '/',
    self.location.origin
  );
  if (targetUrl.origin !== self.location.origin) {
    targetUrl.href = self.location.origin;
  }

  event.waitUntil((async () => {
    const windowClients = await self.clients.matchAll({
      type: 'window',
      includeUncontrolled: true,
    });
    for (const client of windowClients) {
      if ('navigate' in client) await client.navigate(targetUrl.href);
      return client.focus();
    }
    return self.clients.openWindow(targetUrl.href);
  })());
});
