import graphene
from graphene import ObjectType, String, Int, List, Boolean, Field, Mutation, Schema
from tinydb import Query, TinyDB

# Initialize the database
db = TinyDB('db.json')
todos_table = db.table('todos')
users_table = db.table('users')

# Define the Todo type
class TodoType(ObjectType):
    id = Int()
    title = String()
    description = String()
    time = String()
    images = List(String)

# Define the User type
class UserType(ObjectType):
    email = String()
    pro_license = Boolean()

# Define queries
class Query(ObjectType):
    todos = List(TodoType, email=String(required=True))
    user = Field(UserType, email=String(required=True))

    def resolve_todos(root, info, email):
        User = Query()
        return [TodoType(**todo) for todo in todos_table.search(User.email == email)]

    def resolve_user(root, info, email):
        User = Query()
        user = users_table.get(User.email == email)
        if user:
            return UserType(email=user['email'], pro_license=user.get('_pro_license', False))
        return None

# Define mutations
class AddTodoMutation(Mutation):
    class Arguments:
        email = String(required=True)
        title = String(required=True)
        description = String(required=True)
        time = String(required=True)
        images = List(String)

    todo = Field(TodoType)

    def mutate(root, info, email, title, description, time, images):
        new_todo = {
            'email': email,
            'title': title,
            'description': description,
            'time': time,
            'images': images
        }
        doc_id = todos_table.insert(new_todo)
        return AddTodoMutation(todo=TodoType(id=doc_id, **new_todo))

class UpdateTodoMutation(Mutation):
    class Arguments:
        id = Int(required=True)
        title = String()
        description = String()
        time = String()
        images = List(String)

    todo = Field(TodoType)

    def mutate(root, info, id, title=None, description=None, time=None, images=None):
        updates = {}
        if title is not None:
            updates['title'] = title
        if description is not None:
            updates['description'] = description
        if time is not None:
            updates['time'] = time
        if images is not None:
            updates['images'] = images

        todos_table.update(updates, doc_ids=[id])
        updated_todo = todos_table.get(doc_id=id)
        return UpdateTodoMutation(todo=TodoType(id=id, **updated_todo))

class DeleteTodoMutation(Mutation):
    class Arguments:
        id = Int(required=True)

    success = Boolean()

    def mutate(root, info, id):
        todos_table.remove(doc_ids=[id])
        return DeleteTodoMutation(success=True)

class AddUserMutation(Mutation):
    class Arguments:
        email = String(required=True)

    user = Field(UserType)

    def mutate(root, info, email):
        existing_user = users_table.get(Query().email == email)
        if not existing_user:
            user = {
                'email': email,
                '_pro_license': False
            }
            users_table.insert(user)
            return AddUserMutation(user=UserType(email=email, pro_license=False))
        return AddUserMutation(user=UserType(email=email, pro_license=existing_user.get('_pro_license', False)))

class ActivateProLicenseMutation(Mutation):
    class Arguments:
        email = String(required=True)

    success = Boolean()

    def mutate(root, info, email):
        users_table.update({'_pro_license': True}, Query().email == email)
        return ActivateProLicenseMutation(success=True)

# Define the schema
class Mutation(ObjectType):
    add_todo = AddTodoMutation.Field()
    update_todo = UpdateTodoMutation.Field()
    delete_todo = DeleteTodoMutation.Field()
    add_user = AddUserMutation.Field()
    activate_pro_license = ActivateProLicenseMutation.Field()

schema = Schema(query=Query, mutation=Mutation)
