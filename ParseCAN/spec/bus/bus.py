from dataclasses import dataclass
from typing import Sequence, Union

from ... import spec, plural
from . import Message


def _message_constr(key, message):
    if isinstance(message, dict):
        try:
            return Message(name=key, **message)
        except Exception as e:
            e.args = ('in message {}: {}'.format(key, e),)

            raise

    raise ValueError(f'malformed message representation {key}: {message}')


MessageUnique = plural.Unique[Message].make('MessageUnique', ['name', 'id'])


@dataclass
class Bus:
    '''
    A (CAN) bus specification.
    Describes the set of messages that flow through a CAN bus.
    Can unpack CAN Messages that were sent based on this spec.bus.
    '''

    name: str
    baudrate: int
    extended: bool = False
    messages: MessageUnique = MessageUnique()

    def __post_init__(self):
        messages = self.messages
        self.messages = MessageUnique()

        if isinstance(messages, dict):
            messages = [_message_constr(k, v) for k, v in messages.items()]

        self.messages.extend(messages)

    def unpack(self, frame, **kwargs):
        ret = {}
        for msg in self.messages:
            potential = msg.unpack(frame, **kwargs)

            if potential:
                ret[msg.name] = potential

        return ret

    def __str__(self):
        return self.name


class BusFiltered(Bus):
    def __init__(self, bus: Bus, interests: Sequence[Union[int, str]]):
        self.bus = bus
        self.interests = interests

    @property
    def interests(self):
        return self._interests

    @interests.setter
    def interests(self, interests):
        for interest in interests:
            try:
                if isinstance(interest, int):
                    self.bus.messages.id[interest]
                elif isinstance(interest, str):
                    self.bus.messages.name[interest]
                else:
                    raise ValueError(f'in bus {self.bus}: '
                                     f'in interest {interest}: '
                                     'must be of type int or str')
            except KeyError:
                raise KeyError(f'in bus {self.bus}: '
                               f'in interest {interest}: '
                               'does not exist in the bus')

        self._interests = interests

    def interested(self, msg):
        assert isinstance(msg, spec.message)
        return msg.name in self.interests or msg.id in self.interests

    @property
    def messages(self):
        return filter(self.interested, self.bus.messages)

    def __getattr__(self, attr):
        return getattr(self.bus, attr)
