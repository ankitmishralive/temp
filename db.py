

from tinydb import TinyDB, Query

# Initialize TinyDB
db = TinyDB('db.json')
todos_table = db.table('todos')
users_table = db.table('users')

def add_user(email, password_hash):
    users_table.insert({'email': email, 'password': password_hash})

def get_user(email):
    User = Query()
    return users_table.get(User.email == email)

def add_todo(user_email, title, description, time, images=[]):
    todos_table.insert({
        'user_email': user_email,
        'title': title,
        'description': description,
        'time': time,
        'images': images
    })

def get_todos(user_email):
    Todo = Query()
    return todos_table.search(Todo.user_email == user_email)

def delete_todo(todo_id):
    Todo = Query()
    todos_table.remove(Todo.doc_id == todo_id)

def update_todo(todo_id, title=None, description=None, time=None, images=None):
    update_fields = {}
    if title is not None:
        update_fields['title'] = title
    if description is not None:
        update_fields['description'] = description
    if time is not None:
        update_fields['time'] = time
    if images is not None:
        update_fields['images'] = images

    todos_table.update(update_fields, doc_ids=[todo_id])
