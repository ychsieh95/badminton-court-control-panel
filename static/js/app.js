(() => {
  const root = document.documentElement;
  const themeSelect = document.querySelector('#theme-select');
  const savedTheme = localStorage.getItem('court-theme') || 'light';
  const savedPalette = localStorage.getItem('court-palette') || 'yellow';
  if (themeSelect) {
    themeSelect.value = `${savedPalette}:${savedTheme}`;
    if (!themeSelect.value) {
      themeSelect.value = 'yellow:light';
      root.dataset.palette = 'yellow';
      root.dataset.theme = 'light';
    }
    themeSelect.addEventListener('change', () => {
      const [palette, mode] = themeSelect.value.split(':');
      root.dataset.palette = palette;
      root.dataset.theme = mode;
      localStorage.setItem('court-palette', palette);
      localStorage.setItem('court-theme', mode);
    });
  }

  const languageSelect = document.querySelector('#language-select');
  languageSelect?.addEventListener('change', () => {
    document.cookie = `court_lang=${languageSelect.value};path=/;max-age=31536000;samesite=lax`;
    window.location.reload();
  });

  const firstVisitPrompt = document.querySelector('[data-first-visit-prompt]');
  const firstVisitStorageKey = 'court-introduction-prompt-seen-v1';
  if (firstVisitPrompt) {
    const introductionUrl = firstVisitPrompt.dataset.introductionUrl;
    const isIntroductionPage = window.location.pathname === introductionUrl;
    const rememberIntroductionChoice = () => {
      try {
        localStorage.setItem(firstVisitStorageKey, '1');
      } catch {
        // The prompt still works for this page when browser storage is unavailable.
      }
    };
    let hasSeenIntroductionPrompt = false;
    try {
      hasSeenIntroductionPrompt = localStorage.getItem(firstVisitStorageKey) === '1';
    } catch {
      // Treat unavailable browser storage as a new visit.
    }

    if (isIntroductionPage) {
      rememberIntroductionChoice();
    } else if (!hasSeenIntroductionPrompt) {
      firstVisitPrompt.hidden = false;
    }

    firstVisitPrompt
      .querySelector('[data-first-visit-accept]')
      ?.addEventListener('click', rememberIntroductionChoice);
    firstVisitPrompt
      .querySelector('[data-first-visit-decline]')
      ?.addEventListener('click', () => {
        rememberIntroductionChoice();
        firstVisitPrompt.remove();
      });
  }

  const pushNotificationPanel = document.querySelector(
    '[data-push-notification-panel]'
  );
  if (pushNotificationPanel) {
    const pushToggle = pushNotificationPanel.querySelector(
      '[data-push-notification-toggle]'
    );
    const pushStatus = pushNotificationPanel.querySelector(
      '[data-push-notification-status]'
    );
    const setPushStatus = (statusKey) => {
      if (pushStatus) {
        pushStatus.textContent = pushNotificationPanel.dataset[statusKey] || '';
      }
    };
    const urlBase64ToUint8Array = (value) => {
      const padding = '='.repeat((4 - (value.length % 4)) % 4);
      const base64 = (value + padding).replace(/-/g, '+').replace(/_/g, '/');
      return Uint8Array.from(window.atob(base64), (character) => (
        character.charCodeAt(0)
      ));
    };
    const pushRequest = async (url, method, body) => {
      const response = await window.fetch(url, {
        method,
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': pushNotificationPanel.dataset.pushCsrfToken,
        },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error(`Push request failed: ${response.status}`);
      return response.json();
    };

    if (pushNotificationPanel.dataset.pushEnabled !== 'true') {
      setPushStatus('statusUnavailable');
    } else if (
      !('serviceWorker' in navigator)
      || !('PushManager' in window)
      || !('Notification' in window)
    ) {
      setPushStatus('statusUnsupported');
    } else if (Notification.permission === 'denied') {
      setPushStatus('statusDenied');
    } else {
      (async () => {
        let registration;
        try {
          registration = await navigator.serviceWorker.register(
            '/service-worker.js',
            { scope: '/' }
          );
          registration = await navigator.serviceWorker.ready;
          const existingSubscription = await registration.pushManager.getSubscription();
          if (existingSubscription) {
            const state = await pushRequest(
              pushNotificationPanel.dataset.pushStatusUrl,
              'POST',
              { endpoint: existingSubscription.endpoint }
            );
            pushToggle.checked = Boolean(state.subscribed);
          }
          setPushStatus(
            pushToggle.checked ? 'statusEnabled' : 'statusDisabled'
          );
          pushToggle.disabled = false;
        } catch {
          pushToggle.checked = false;
          pushToggle.disabled = true;
          setPushStatus('statusError');
          return;
        }

        pushToggle.addEventListener('change', async () => {
          const wantsNotifications = pushToggle.checked;
          pushToggle.disabled = true;
          setPushStatus(
            wantsNotifications ? 'statusEnabling' : 'statusDisabling'
          );
          try {
            if (wantsNotifications) {
              const permission = Notification.permission === 'granted'
                ? 'granted'
                : await Notification.requestPermission();
              if (permission !== 'granted') {
                pushToggle.checked = false;
                setPushStatus(
                  permission === 'denied' ? 'statusDenied' : 'statusDisabled'
                );
                return;
              }
            }
            let subscription = await registration.pushManager.getSubscription();
            if (wantsNotifications) {
              if (!subscription) {
                subscription = await registration.pushManager.subscribe({
                  userVisibleOnly: true,
                  applicationServerKey: urlBase64ToUint8Array(
                    pushNotificationPanel.dataset.pushPublicKey
                  ),
                });
              }
              await pushRequest(
                pushNotificationPanel.dataset.pushSubscribeUrl,
                'POST',
                { subscription: subscription.toJSON() }
              );
              setPushStatus('statusEnabled');
            } else {
              if (subscription) {
                await pushRequest(
                  pushNotificationPanel.dataset.pushSubscribeUrl,
                  'DELETE',
                  { endpoint: subscription.endpoint }
                );
              }
              setPushStatus('statusDisabled');
            }
          } catch {
            pushToggle.checked = !wantsNotifications;
            setPushStatus('statusError');
          } finally {
            pushToggle.disabled = Notification.permission === 'denied';
          }
        });
      })();
    }
  }

  document.querySelectorAll('.flash-close').forEach((button) => {
    button.addEventListener('click', () => button.closest('.flash')?.remove());
  });

  const dropdownMenus = document.querySelectorAll(
    '.account-menu, .court-action-menu, .preferences-menu, .participant-admin-menu'
  );
  document.addEventListener('click', (event) => {
    dropdownMenus.forEach((menu) => {
      if (menu.open && !menu.contains(event.target)) menu.removeAttribute('open');
    });
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    dropdownMenus.forEach((menu) => {
      if (!menu.open) return;
      menu.removeAttribute('open');
      menu.querySelector('summary')?.focus();
    });
  });

  const avatarInput = document.querySelector('[data-avatar-input]');
  const avatarPreview = document.querySelector('[data-avatar-preview]');
  let avatarPreviewUrl;
  avatarInput?.addEventListener('change', () => {
    const file = avatarInput.files?.[0];
    if (!file || !avatarPreview) return;
    if (avatarPreviewUrl) URL.revokeObjectURL(avatarPreviewUrl);
    avatarPreviewUrl = URL.createObjectURL(file);
    const image = document.createElement('img');
    image.src = avatarPreviewUrl;
    image.alt = '';
    avatarPreview.replaceChildren(image);
  });

  const tempPasswordDialog = document.querySelector('#temp-password-dialog');
  const tempPasswordForm = tempPasswordDialog?.querySelector('[data-temp-password-form]');
  const tempPasswordUsername = tempPasswordDialog?.querySelector('[data-temp-password-username]');
  const tempPasswordInput = tempPasswordDialog?.querySelector('[data-temp-password-input]');
  document.querySelectorAll('.temp-password-trigger').forEach((trigger) => {
    trigger.addEventListener('click', () => {
      if (!tempPasswordDialog || !tempPasswordForm) return;
      tempPasswordForm.action = trigger.dataset.tempPasswordUrl;
      if (tempPasswordUsername) tempPasswordUsername.textContent = trigger.dataset.tempPasswordUser;
      tempPasswordDialog.showModal();
      tempPasswordInput?.focus();
    });
  });
  tempPasswordDialog?.querySelectorAll('[data-dialog-close]').forEach((button) => {
    button.addEventListener('click', () => tempPasswordDialog.close());
  });
  tempPasswordDialog?.addEventListener('click', (event) => {
    if (event.target === tempPasswordDialog) tempPasswordDialog.close();
  });
  tempPasswordDialog?.addEventListener('close', () => {
    if (tempPasswordInput) tempPasswordInput.value = '';
  });

  document.querySelectorAll('form[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  document.querySelectorAll('.join-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;
      document.querySelectorAll('.join-tab').forEach((item) => {
        const active = item === tab;
        item.classList.toggle('active', active);
        item.setAttribute('aria-selected', String(active));
      });
      document.querySelectorAll('.tab-content').forEach((panel) => {
        const active = panel.dataset.panel === target;
        panel.classList.toggle('active', active);
        panel.hidden = !active;
      });
    });
  });

  const joinPanel = document.querySelector('[data-join-panel]');
  const mobileJoinTrigger = document.querySelector('[data-mobile-join-trigger]');
  const mobileJoinDialog = document.querySelector('[data-mobile-join-dialog]');
  const mobileJoinContent = document.querySelector(
    '[data-mobile-join-dialog-content]'
  );
  if (
    joinPanel
    && mobileJoinTrigger
    && mobileJoinDialog
    && mobileJoinContent
  ) {
    const panelMarker = document.createComment('join-panel-location');
    joinPanel.before(panelMarker);
    const mobileJoinMedia = window.matchMedia('(max-width: 720px)');
    const syncMobileJoinPanel = () => {
      if (mobileJoinMedia.matches) {
        mobileJoinContent.append(joinPanel);
      } else {
        if (mobileJoinDialog.open) mobileJoinDialog.close();
        panelMarker.after(joinPanel);
      }
    };
    mobileJoinTrigger.addEventListener('click', () => {
      syncMobileJoinPanel();
      if (!mobileJoinDialog.open) mobileJoinDialog.showModal();
    });
    mobileJoinDialog
      .querySelector('[data-mobile-join-close]')
      ?.addEventListener('click', () => mobileJoinDialog.close());
    mobileJoinDialog.addEventListener('click', (event) => {
      if (event.target !== mobileJoinDialog) return;
      const bounds = mobileJoinDialog.getBoundingClientRect();
      const inside = (
        event.clientX >= bounds.left
        && event.clientX <= bounds.right
        && event.clientY >= bounds.top
        && event.clientY <= bounds.bottom
      );
      if (!inside) mobileJoinDialog.close();
    });
    mobileJoinMedia.addEventListener?.('change', syncMobileJoinPanel);
    syncMobileJoinPanel();
  }

  document.querySelectorAll('[data-copy]').forEach((button) => {
    button.addEventListener('click', async () => {
      const label = button.querySelector('span');
      try {
        await navigator.clipboard.writeText(button.dataset.copy);
        label.textContent = label.dataset.copiedLabel;
        setTimeout(() => { label.textContent = label.dataset.copyLabel; }, 1800);
      } catch {
        window.prompt(label.dataset.copyLabel, button.dataset.copy);
      }
    });
  });

  const hallName = document.querySelector('#hall-name');
  const hallLocation = document.querySelector('#hall-location');
  const mapsLink = document.querySelector('#maps-search-link');
  const updateMapsLink = () => {
    if (!mapsLink) return;
    const searchInput = document.querySelector('#hall-place-autocomplete');
    const query = [searchInput?.value || hallName?.value, hallLocation?.value]
      .filter(Boolean)
      .join(' ');
    mapsLink.href = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
  };
  hallName?.addEventListener('input', updateMapsLink);
  hallLocation?.addEventListener('input', updateMapsLink);
  updateMapsLink();

  document.querySelectorAll('[data-time24]').forEach((input) => {
    input.addEventListener('input', () => {
      const raw = input.value.replace(/[^\d:]/g, '');
      if (raw.includes(':')) {
        const [hour, ...minuteParts] = raw.split(':');
        input.value = `${hour.slice(0, 2)}:${minuteParts.join('').slice(0, 2)}`;
        return;
      }
      const digits = raw.slice(0, 4);
      input.value = digits.length > 2 ? `${digits.slice(0, 2)}:${digits.slice(2)}` : digits;
    });
    input.addEventListener('blur', () => {
      const match = input.value.match(/^(\d):(\d{2})$/);
      if (match) input.value = `0${match[1]}:${match[2]}`;
    });
  });

  const filterDateInputs = document.querySelectorAll('[data-filter-date]');
  const formatDateDigits = (value) => {
    const digits = value.replace(/\D/g, '').slice(0, 8);
    if (digits.length <= 4) return digits;
    if (digits.length <= 6) return `${digits.slice(0, 4)}/${digits.slice(4)}`;
    return `${digits.slice(0, 4)}/${digits.slice(4, 6)}/${digits.slice(6)}`;
  };
  const parseFilterDate = (value) => {
    const match = value.match(/^(\d{4})[/-](\d{2})[/-](\d{2})$/);
    if (!match) return null;
    const parsed = new Date(Date.UTC(
      Number.parseInt(match[1], 10),
      Number.parseInt(match[2], 10) - 1,
      Number.parseInt(match[3], 10),
    ));
    if (
      parsed.getUTCFullYear() !== Number.parseInt(match[1], 10)
      || parsed.getUTCMonth() !== Number.parseInt(match[2], 10) - 1
      || parsed.getUTCDate() !== Number.parseInt(match[3], 10)
    ) return null;
    return parsed;
  };
  const formatFilterDate = (value) => [
    value.getUTCFullYear(),
    String(value.getUTCMonth() + 1).padStart(2, '0'),
    String(value.getUTCDate()).padStart(2, '0'),
  ].join('/');

  const courtDateInput = document.querySelector('[data-court-date]');
  const courtWeekdayOutput = document.querySelector('[data-court-weekday]');
  const updateCourtWeekday = () => {
    if (!courtDateInput || !courtWeekdayOutput) return;
    const parsed = parseFilterDate(courtDateInput.value);
    if (!parsed) {
      courtWeekdayOutput.textContent = '';
      return;
    }
    const weekdayNames = [
      courtWeekdayOutput.dataset.weekdaySunday,
      courtWeekdayOutput.dataset.weekdayMonday,
      courtWeekdayOutput.dataset.weekdayTuesday,
      courtWeekdayOutput.dataset.weekdayWednesday,
      courtWeekdayOutput.dataset.weekdayThursday,
      courtWeekdayOutput.dataset.weekdayFriday,
      courtWeekdayOutput.dataset.weekdaySaturday,
    ];
    courtWeekdayOutput.textContent = weekdayNames[parsed.getUTCDay()] || '';
  };
  courtDateInput?.addEventListener('input', updateCourtWeekday);
  courtDateInput?.addEventListener('change', updateCourtWeekday);
  updateCourtWeekday();

  const leaveDeadlineToggle = document.querySelector('[data-leave-deadline-toggle]');
  const leaveDeadlineField = document.querySelector('[data-leave-deadline-field]');
  const leaveDeadlineInput = document.querySelector('[data-leave-deadline-input]');
  const updateLeaveDeadline = () => {
    if (!leaveDeadlineToggle || !leaveDeadlineField || !leaveDeadlineInput) return;
    const enabled = leaveDeadlineToggle.checked;
    leaveDeadlineField.hidden = !enabled;
    leaveDeadlineInput.required = enabled;
  };
  leaveDeadlineToggle?.addEventListener('change', updateLeaveDeadline);
  updateLeaveDeadline();

  filterDateInputs.forEach((input) => {
    input.addEventListener('input', () => {
      input.value = formatDateDigits(input.value);
    });
    input.addEventListener('blur', () => {
      const parsed = parseFilterDate(input.value);
      if (parsed) input.value = formatFilterDate(parsed);
    });
  });

  const dateFromInput = document.querySelector('[data-date-from]');
  const dateToInput = document.querySelector('[data-date-to]');
  let previousFromDate = dateFromInput
    ? parseFilterDate(dateFromInput.value)
    : null;
  dateFromInput?.addEventListener('change', () => {
    const nextFromDate = parseFilterDate(dateFromInput.value);
    if (!nextFromDate || !dateToInput) return;
    const currentToDate = parseFilterDate(dateToInput.value);
    if (currentToDate && previousFromDate) {
      const rangeMilliseconds = currentToDate.getTime() - previousFromDate.getTime();
      const nextToDate = new Date(nextFromDate.getTime() + rangeMilliseconds);
      dateToInput.value = formatFilterDate(nextToDate);
    } else if (!currentToDate) {
      dateToInput.value = formatFilterDate(nextFromDate);
    } else if (currentToDate < nextFromDate) {
      dateToInput.value = formatFilterDate(nextFromDate);
    }
    previousFromDate = nextFromDate;
  });

  const courtMediaInput = document.querySelector('[data-court-media-input]');
  const courtMediaPreview = document.querySelector('[data-court-media-preview]');
  let courtMediaPreviewUrls = [];
  courtMediaInput?.addEventListener('change', () => {
    courtMediaPreviewUrls.forEach((url) => URL.revokeObjectURL(url));
    courtMediaPreviewUrls = [];
    if (!courtMediaPreview) return;
    const previews = Array.from(courtMediaInput.files || []).map((file) => {
      const item = document.createElement('div');
      item.className = 'media-upload-preview-item';
      const url = URL.createObjectURL(file);
      courtMediaPreviewUrls.push(url);
      const preview = document.createElement(
        file.type.startsWith('video/') ? 'video' : 'img'
      );
      preview.src = url;
      if (preview instanceof HTMLVideoElement) {
        preview.muted = true;
        preview.preload = 'metadata';
      } else {
        preview.alt = '';
      }
      const name = document.createElement('span');
      name.textContent = file.name;
      item.append(preview, name);
      return item;
    });
    courtMediaPreview.replaceChildren(...previews);
  });

  document.querySelectorAll('[data-event-gallery]').forEach((gallery) => {
    const slides = Array.from(gallery.querySelectorAll('[data-gallery-slide]'));
    const thumbnails = Array.from(
      gallery.querySelectorAll('[data-gallery-thumbnail]')
    );
    thumbnails.forEach((thumbnail) => {
      thumbnail.addEventListener('click', () => {
        const selectedIndex = thumbnail.dataset.galleryThumbnail;
        slides.forEach((slide) => {
          const selected = slide.dataset.gallerySlide === selectedIndex;
          slide.hidden = !selected;
          slide.classList.toggle('is-active', selected);
          if (!selected) slide.querySelector('video')?.pause();
        });
        thumbnails.forEach((item) => {
          const selected = item === thumbnail;
          item.classList.toggle('is-active', selected);
          item.setAttribute('aria-pressed', selected ? 'true' : 'false');
        });
        thumbnail.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
          inline: 'nearest',
        });
      });
    });
  });

  const orderedCount = document.querySelector('#ordered-count');
  const reservedNicknameList = document.querySelector('#reserved-nickname-list');
  const syncReservedNicknameFields = () => {
    if (!orderedCount || !reservedNicknameList) return;
    // Preserve existing names while the organizer temporarily clears the
    // number field to type a replacement value.
    if (orderedCount.value.trim() === '') return;
    const requestedCount = Number.parseInt(orderedCount.value, 10);
    const count = Number.isFinite(requestedCount)
      ? Math.max(0, Math.min(99, requestedCount))
      : 0;
    let fields = Array.from(
      reservedNicknameList.querySelectorAll('.reserved-nickname-field')
    );
    while (fields.length > count) {
      fields.pop().remove();
    }
    while (fields.length < count) {
      const field = document.createElement('label');
      field.className = 'field reserved-nickname-field';
      const label = document.createElement('span');
      const input = document.createElement('input');
      input.name = 'reserved_nickname';
      input.maxLength = 40;
      input.placeholder = reservedNicknameList.dataset.placeholder || '';
      field.append(label, input);
      reservedNicknameList.append(field);
      fields.push(field);
    }
    fields.forEach((field, index) => {
      const label = field.querySelector('span');
      if (label) {
        label.textContent = `${reservedNicknameList.dataset.label || ''} ${index + 1}`;
      }
    });
  };
  orderedCount?.addEventListener('input', syncReservedNicknameFields);
  syncReservedNicknameFields();
})();

(() => {
  const savedLocationSelect = document.querySelector('[data-saved-location-select]');
  if (!savedLocationSelect) return;

  savedLocationSelect.addEventListener('change', () => {
    const option = savedLocationSelect.selectedOptions[0];
    if (!option?.value) return;

    // Synchronize Places before filling the saved metadata. Its input handler
    // updates the tracked search query and may clear stale place details.
    const autocomplete = document.querySelector('#hall-place-autocomplete');
    if (autocomplete) {
      autocomplete.value = option.dataset.hallName || '';
      autocomplete.dispatchEvent(new Event('input', { bubbles: true }));
    }

    const values = {
      '#hall-name': option.dataset.hallName || '',
      '#hall-location': option.dataset.location || '',
      '#google-place-id': option.dataset.googlePlaceId || '',
      '#hall-latitude': option.dataset.latitude || '',
      '#hall-longitude': option.dataset.longitude || '',
    };
    Object.entries(values).forEach(([selector, value]) => {
      const input = document.querySelector(selector);
      if (input) {
        input.value = value;
        input.dispatchEvent(new Event('input', { bubbles: true }));
      }
    });
  });
})();

(() => {
  const dialog = document.querySelector('#role-dialog');
  const form = dialog?.querySelector('[data-role-dialog-form]');
  const username = dialog?.querySelector('[data-role-dialog-username]');
  const options = dialog?.querySelectorAll('[data-role-option]') || [];

  document.querySelectorAll('[data-role-dialog-trigger]').forEach((trigger) => {
    trigger.addEventListener('click', (event) => {
      event.preventDefault();
      if (!dialog || !form) return;
      form.action = trigger.dataset.roleUrl || '';
      if (username) username.textContent = trigger.dataset.roleUser || '';
      options.forEach((option) => {
        const isCurrent = option.dataset.roleOption === trigger.dataset.currentRole;
        option.disabled = isCurrent;
        option.classList.toggle('current', isCurrent);
      });
      dialog.showModal();
      dialog.querySelector('[data-role-option]:not(:disabled)')?.focus();
    });
  });

  dialog?.querySelectorAll('[data-role-dialog-close]').forEach((button) => {
    button.addEventListener('click', () => dialog.close());
  });
  dialog?.addEventListener('click', (event) => {
    if (event.target === dialog) dialog.close();
  });
})();

window.initPlacesAutocomplete = async () => {
  const host = document.querySelector('#hall-autocomplete-host');
  const selectedName = document.querySelector('#hall-name');
  const location = document.querySelector('#hall-location');
  const placeId = document.querySelector('#google-place-id');
  const latitude = document.querySelector('#hall-latitude');
  const longitude = document.querySelector('#hall-longitude');
  const status = document.querySelector('#place-search-status');
  if (!host || !selectedName || !location || !window.google?.maps?.importLibrary) return;

  try {
    const { PlaceAutocompleteElement } = await google.maps.importLibrary('places');
    const autocomplete = new PlaceAutocompleteElement();
    autocomplete.id = 'hall-place-autocomplete';
    autocomplete.placeholder = host.dataset.placeholder || '';
    autocomplete.description = host.dataset.description || '';
    autocomplete.includedRegionCodes = ['tw'];
    autocomplete.requestedLanguage =
      document.documentElement.lang.toLowerCase() === 'zh-tw' ? 'zh-TW' : 'en-US';
    autocomplete.requestedRegion = 'tw';
    autocomplete.maxlength = 160;

    // Intentionally do not set includedPrimaryTypes: badminton halls may be
    // classified under several different Google place types.
    host.appendChild(autocomplete);

    let lastSearchQuery = autocomplete.value.trim();
    const updateSearchLink = () => {
      document.querySelector('#maps-search-link')?.setAttribute(
        'href',
        `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
          [autocomplete.value, location.value].filter(Boolean).join(' ')
        )}`
      );
    };
    const syncTypedHall = () => {
      const query = autocomplete.value.trim();
      if (query === lastSearchQuery) return;
      lastSearchQuery = query;
      selectedName.value = query;
      location.value = '';
      if (placeId) placeId.value = '';
      if (latitude) latitude.value = '';
      if (longitude) longitude.value = '';
      if (status) status.textContent = '';
      updateSearchLink();
    };

    // PlaceAutocompleteElement exposes `value`, but its documented events only
    // guarantee selection/error events. Polling the lightweight value property
    // keeps the selected-hall field in sync while the user is still typing.
    autocomplete.addEventListener('input', syncTypedHall);
    const syncTimer = window.setInterval(syncTypedHall, 120);

    autocomplete.addEventListener('gmp-select', async ({ placePrediction }) => {
      const place = placePrediction.toPlace();
      selectedName.value = autocomplete.value.trim();
      if (placeId) placeId.value = place.id ?? '';
      try {
        await place.fetchFields({
          fields: ['displayName', 'formattedAddress', 'location'],
        });
        selectedName.value = place.displayName ?? '';
        location.value = place.formattedAddress ?? '';
        if (placeId) placeId.value = place.id ?? '';
        if (latitude) latitude.value = place.location?.lat()?.toString() ?? '';
        if (longitude) longitude.value = place.location?.lng()?.toString() ?? '';
        lastSearchQuery = autocomplete.value.trim();
        if (status) status.textContent = '';
        location.dispatchEvent(new Event('input'));
      } catch (error) {
        if (status) status.textContent = host.dataset.error || '';
        console.error('Unable to fetch Google place details:', error);
      }
    });
    autocomplete.addEventListener('gmp-error', () => {
      window.clearInterval(syncTimer);
      window.enableManualHallFallback();
    });
  } catch (error) {
    window.enableManualHallFallback();
    console.error('Unable to initialize Google place search:', error);
  }
};

window.enableManualHallFallback = () => {
  const host = document.querySelector('#hall-autocomplete-host');
  const status = document.querySelector('#place-search-status');
  const selectedName = document.querySelector('#hall-name');
  const location = document.querySelector('#hall-location');
  if (selectedName) selectedName.readOnly = false;
  if (location) location.readOnly = false;
  if (host) host.replaceChildren();
  if (host && status) {
    status.textContent = `${host.dataset.apiError || ''} (${window.location.origin}/*)`;
  }
};

// Google invokes this global callback for an invalid or unauthorized Maps key.
window.gm_authFailure = () => {
  window.enableManualHallFallback();
};
