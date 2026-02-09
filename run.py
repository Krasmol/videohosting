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
