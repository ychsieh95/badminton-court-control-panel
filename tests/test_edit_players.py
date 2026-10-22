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
