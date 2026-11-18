"""Bind the fixed queens service to its public RPC methods."""

from .dispatcher import Handler, JsonObject, RpcError
from .solver import InvalidBoardSize
from .streams import InvalidStreamInput, StreamNotFound, StreamTable


def _require_keys(params: JsonObject, *keys: str) -> None:
    if params.keys() != set(keys):
        raise RpcError(-32602, "Invalid params")


def methods_for(streams: StreamTable) -> dict[str, Handler]:
    def health(params: JsonObject) -> JsonObject:
        _require_keys(params)
        return {"status": "ok", "version": "1.0"}

    def open_stream(params: JsonObject) -> JsonObject:
        _require_keys(params, "size")
        size = params["size"]
        try:
            stream_id = streams.open(size)
        except InvalidBoardSize as error:
            raise RpcError(-32602, "Invalid params") from error
        return {"stream_id": stream_id, "size": size}

    def next_events(params: JsonObject) -> JsonObject:
        _require_keys(params, "stream_id", "limit")
        try:
            batch = streams.next(params["stream_id"], params["limit"])
        except InvalidStreamInput as error:
            raise RpcError(-32602, "Invalid params") from error
        except StreamNotFound as error:
            raise RpcError(-32004, "Stream not found") from error
        return {"events": batch.events, "done": batch.done}

    def close_stream(params: JsonObject) -> JsonObject:
        _require_keys(params, "stream_id")
        try:
            streams.close(params["stream_id"])
        except InvalidStreamInput as error:
            raise RpcError(-32602, "Invalid params") from error
        except StreamNotFound as error:
            raise RpcError(-32004, "Stream not found") from error
        return {"closed": True}

    return {
        "service.health": health,
        "queens.open": open_stream,
        "queens.next": next_events,
        "queens.close": close_stream,
    }
