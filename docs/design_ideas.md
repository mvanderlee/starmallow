# Design Ideas

This document will contain some of my design ideas and reasoning for this project.

## Why create another async web framework

FastAPI is the most popular asyncio web framework, however it uses pydantic which has some limitations and was incompatible with a project I worked.
The project used Flask and Marshmallow using Flask-Smorest to do automated validation and OpenAPI generation. While I found some small web frameworks that use Marshmallow, they lacked the easy to use APIs that FastAPI provides.

Therefore I set out to create a web framework that is as easy to use as FastAPI and mimics a lot of it's behaviours, but using Marshmallow instead of pydantic.

## Goals

* Match FastAPIs easy to use APIs
* Use Marshmallow for validation and schema generation
* Support Marshmallow-Dataclass
* Support native data types and create Marshmallow fields behind the scenes.

## To document

Collection of special cases that must be added to to the documentation.

### Default values

Because we allow Python default values, and parameter defaults (like FastAPI). But Marshmallow fields can have their own defaults defined, we can have conflicting default values.
In this case we will always honor the Python or parameter defaults over the Marshmallow defaults.

i.e.:

In the below example, we will use `0` as the default value, not `10`.

```python
def api(
  offset: int = Query(0, model=mf.Integer(missing=10)
):
  pass
```

### Query parameter, json body, or other

Unless specified as a specific param, all Schemas are accepted as json body, and all fields are accepcted as query parameters
