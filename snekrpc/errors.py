class SnekRPCError(Exception):
    """Base class for all errors."""

## transport

class TransportError(SnekRPCError):
    """Raised for any error in the transport."""

## io

class SendInterrupted(TransportError):
    """Raised when data sent to the remote end is less than expected."""

class ReceiveInterrupted(TransportError):
    """Raised when data received from the remote end is less than expected."""

## client

class ClientError(SnekRPCError):
    """Base class for client exceptions."""

# TODO: use these
class InvalidService(ClientError):
    """Raised for any attempt to access a service that does not exist."""

class InvalidCommand(ClientError):
    """Raised for any attempt to access a command that does not exist."""

class RemoteError(ClientError):
    """Raised for any exceptions that occur on the RPC server."""
    def __init__(self, name, msg, traceback):
        self.name = name
        self.msg = msg
        self.traceback = traceback

    @property
    def message(self):
        return '{}: {}'.format(self.name, self.msg)

    def __str__(self):
        return self.traceback or self.message

## server

class ServerError(SnekRPCError):
    """Base class for server exceptions."""

class ParameterError(ServerError):
    """Raised for invalid paramater configurations."""

## protocol

class ProtocolOpError(SnekRPCError):
    """Raised for protocol errors."""
    def __init__(self, opcode):
        super(ProtocolOpError, self).__init__('invalid opcode: {}'.format(opcode))
        self.opcode = opcode

## serialization

class EncodeError(SnekRPCError):
    """Adds context for errors raised when packing."""

class DecodeError(SnekRPCError):
    """Adds context for errors raised when unpacking."""

## registry

class RegistryError(SnekRPCError):
    pass
