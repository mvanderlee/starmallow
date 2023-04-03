from typing import Dict

from starlette.testclient import TestClient

from starmallow import ResolvedParam, StarMallow

app = StarMallow()

state = {
    '/async': "asyncgen not started",
}


# region - Resolvers
async def get_state():
    return state


async def asyncgen_state(state: Dict[str, str] = ResolvedParam(get_state)):
    state["/async"] = "asyncgen started"
    yield state["/async"]
    state["/async"] = "asyncgen completed"
#endregion


# region - Routes
@app.get("/async")
async def get_async(state_gen: str = ResolvedParam(asyncgen_state)):
    return state_gen
#endregion


client = TestClient(app)


# region - tests
def test_async_state():
    assert state["/async"] == "asyncgen not started"
    response = client.get("/async")
    assert response.status_code == 200, response.text
    assert response.json() == "asyncgen started"
    assert state["/async"] == "asyncgen completed"
# endregion
