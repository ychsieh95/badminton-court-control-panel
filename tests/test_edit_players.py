import pytest

from test_app import app, client, create_court, create_member_court, get_db, login, signup


@pytest.mark.parametrize('organizer', [False, True])
def test_edit_page_shows_registered_players(client, app, organizer):
    if organizer:
        signup(client, 'alice')
        location = create_member_court(client, 'Roster event')
        prefix = '/my-courts'
    else:
        login(client)
        location = create_court(client, court_date='2099-08-20')
        prefix = '/admin/courts'
    guid = location.rsplit('/', 1)[-1]
    edit_url = f'{prefix}/{guid}/edit'
    empty = client.get(edit_url)
    assert empty.status_code == 200
    assert '目前尚無線上報名。'.encode() in empty.data
    with app.app_context():
        db = get_db()
        court_id = db.execute('SELECT id FROM courts WHERE guid = ?', (guid,)).fetchone()['id']
        db.executemany(
            'INSERT INTO participants '
            '(court_id, username, username_key, pin_hash, joined_at, waitlisted, roll_called) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            [(court_id, 'Checked Player', 'checked', 'unused', '2026-01-02', 0, 1),
             (court_id, '<Waiting Player>', 'waiting', 'unused', '2026-01-01', 1, 0)],
        )
        db.commit()
    response = client.get(edit_url)
    assert response.status_code == 200
    assert b'Checked Player' in response.data
    assert b'&lt;Waiting Player&gt;' in response.data
    assert response.data.index(b'Checked Player') < response.data.index(b'&lt;Waiting Player&gt;')
    assert '點名 ✓'.encode() in response.data
    assert '候補'.encode() in response.data
    assert b'<span class="count-badge">2</span>' in response.data
    assert b'registered-players-heading' not in client.get('/courts/new').data


@pytest.mark.parametrize('organizer', [False, True])
def test_create_and_edit_sections_restore_cookie_preferences(client, organizer):
    if organizer:
        signup(client, 'alice')
        location = create_member_court(client)
        prefix = '/my-courts'
    else:
        login(client)
        location = create_court(client, court_date='2099-08-20')
        prefix = '/admin/courts'
    guid = location.rsplit('/', 1)[-1]
    sections = ['event', 'hall', 'members', 'price', 'level', 'remark', 'media']
    for url in ['/courts/new', f'{prefix}/{guid}/edit']:
        expanded = client.get(url)
        assert expanded.status_code == 200
        assert b'data-section-navigator' in expanded.data
        for section in sections:
            assert f'data-court-section="form-{section}" open>'.encode() in expanded.data
            assert f'id="form-section-{section}"'.encode() in expanded.data
        if url == '/courts/new':
            assert b'data-court-section="form-import" open>' in expanded.data
            assert b'id="form-section-import"' in expanded.data
        else:
            assert b'id="form-section-import"' not in expanded.data
        client.set_cookie('court_section_form-members', 'collapsed')
        collapsed = client.get(url)
        assert b'data-court-section="form-members">' in collapsed.data
        assert b'data-court-section="form-event" open>' in collapsed.data
        # Form preferences do not change the public court section preferences.
        assert b'data-court-section="capacity" open>' in client.get(location).data
        client.set_cookie('court_section_form-members', 'expanded')


def test_form_sections_with_errors_expand_despite_saved_preference(client):
    from test_app import csrf

    login(client)
    for section in ['event', 'remark', 'import']:
        client.set_cookie(f'court_section_form-{section}', 'collapsed')
    response = client.post('/courts/new', data={
        'csrf_token': csrf(client, '/courts/new'),
        'court_date': 'invalid',
    })
    assert response.status_code == 200
    assert b'data-court-section="form-event" open>' in response.data
    assert b'data-court-section="form-remark">' in response.data
    assert b'data-court-section="form-import">' in response.data

    failed_import = client.post('/courts/new', data={
        'csrf_token': csrf(client, '/courts/new'),
        'form_action': 'import_court_info',
    })
    assert b'data-court-section="form-import" open>' in failed_import.data
