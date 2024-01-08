# StarMallow

StarMallow is a starlette based web framework for building robust APIs with Python and Marshmallow.
It's been inspired by FastAPI, but uses [Marshmallow](https://marshmallow.readthedocs.io/en/stable/) instead of [Pydantic](https://docs.pydantic.dev/) for it's schema definitions.
It's reason for existing is simply because marshmallow is a much more powerful serialization engine, and in most cases it's fast enough.
An example of Pydantic's limitations can be found in [Issue 2277](https://github.com/pydantic/pydantic/issues/2277)

## Example

### Create it

Create a file `main.py` with:

```python
from typing import Annotated
from marshmallow_dataclass import dataclass
from starmallow import Body, Path, StarMallow

app = StarMallow()

# Minimum example
@app.get("/path/{item_id}")
def get_id(item_id):
    return item_id


# Example with explicit location option
@dataclass
class MyBody:
    item_id: int
    sub_item_id: int


@app.get("/body")
async def get_body(body: MyBody = Body()) -> int:
    return body.item_id


# Example with explicit marshmallow schema
class MyBodySchema(ma.Schema):
    item_id = mf.Integer()

@app.get("/path/body_schema")
def get_body_from_schema(body: Dict[str, int] = Body(model=MyBodySchema)) -> int:
    return body['item_id']


# Example with Annotated

@app.get("/body_annotated")
async def get_body_annotated(body: Annotated[MyBody, Body()]) -> int:
    return body.item_id
```

### Run it

Run the server with:

```shell
❯ uvicorn sample_server:app --reload

INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [84092]
INFO:     Started server process [87944]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### View the docs

* Open the browser at [http://localhost:8000/docs](http://localhost:8000/docs) to view the Swagger UI.
* Open the browser at [http://localhost:8000/redoc](http://localhost:8000/redoc) to view the Redoc UI.

## HTTP Endpoints

You can also use class-based views. This can make it easier to organize your code and gives you an easy migration path if you use [flask-smorest](https://flask-smorest.readthedocs.io/)

```python
from marshmallow_dataclass import dataclass
from starmallow import StarMallow
from starmallow.decorators import route
from starmallow.endpoints import APIHTTPEndpoint


app = StarMallow()


@dataclass
class Pet:
    name: str


@app.api_route('/')
class Pets(APIHTTPEndpoint):
    def get(self) -> Pet:
        return Pet.get()

    def post(self, pet: Pet) -> Pet:
        pet.create()
        return pet


@app.api_route('/id/{pet_id}')
class PetById(ApiHttpEndpoint):
    @route(deprecated=True)  # Specify @route if you need to override parameters
    def get(self, pet_id: int) -> Pet:
        return Pet.get(pet_id)


    @route(status_code=204)  # Specify @route if you need to override parameters
    def get(self, pet_id: int):
        Pet.get(pet_id).delete()
```

## Optional Dependencies

* [`uvicorn`](https://www.uvicorn.org) - for the server that loads and serves your application.
* [`orjson`](https://github.com/ijl/orjson) - Required if you want to use `ORJSONResponse`.
* [`ujson`](https://github.com/esnme/ultrajson) - Required if you want to use `UJSONResponse`.
