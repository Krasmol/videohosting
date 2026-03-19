# Видеохостинг - учебный проект группы [ИСП 33-9]
# Copyright (C) [2026] [Иван, Дмитрий, Роман, Савелий, Арсений, Кирилл]
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app, socketio, db

app = create_app()


@app.cli.command()
def init_db():
    with app.app_context():
        db.create_all()
        print('Database initialized successfully.')


@app.cli.command()
def drop_db():
    with app.app_context():
        if input('Are you sure you want to drop all tables? (yes/no): ').lower() == 'yes':
            db.drop_all()
            print('Database tables dropped.')
        else:
            print('Operation cancelled.')


@app.shell_context_processor
def make_shell_context():
    from app import models
    return {
        'db': db,
        'app': app
    }


if __name__ == '__main__':
    # Do NOT hardcode a LAN IP here. If the IP doesn't exist on the user's machine,
    # the server won't start and the frontend will show "connection to server" errors.
    host = os.environ.get('HOST', '192.168.1.15')
    port = int(os.environ.get('PORT', '5000'))
    socketio.run(
        app,
        host=host,
        port=port,
        debug=app.config['DEBUG'],
        allow_unsafe_werkzeug=True
    )
