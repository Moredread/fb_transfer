#!/usr/bin/env python

from __future__ import print_function

from SOAPpy import SOAPProxy
import time
import sys
import collections


TrafficInfo = collections.namedtuple('TrafficInfo', [
    'total_recv',
    'total_sent',
    'rate_recv',
    'rate_send',
])


def _get_raw_traffic_info(soap):
    info = soap.GetAddonInfos()
    return TrafficInfo(
        long(info['NewTotalBytesReceived']),
        long(info['NewTotalBytesSent']),
        int(info['NewByteReceiveRate']),
        int(info['NewByteSendRate']))


def _clear_line(file):
    file.write("\r\033[K")
    file.flush()


def monitor_traffic(sample_time=1.0, integr_count=1, fb_url='fritz.box:49000'):

    soap = SOAPProxy(
        proxy='http://{}/igdupnp/control/WANCommonIFC1'.format(fb_url),
        namespace='http://{}/igdupnp/control/WANCommonIFC1'.format(fb_url),
        soapaction='urn:schemas-upnp-org:service:WANCommonInterfaceConfig:1#GetAddonInfos',
        noroot=True)

    history = collections.deque(maxlen=integr_count)

    start_info = _get_raw_traffic_info(soap)
    start_time = time.time()
    history.append((start_time, start_info))
    recv_overflows = 0L
    send_overflows = 0L

    yield TrafficInfo(0, 0, start_info.rate_recv, start_info.rate_send)

    while True:
        time.sleep(sample_time)

        comp_time, comp_info = history[0]
        prev_time, prev_info = history[-1]

        cur_info = _get_raw_traffic_info(soap)
        cur_time = time.time()
        history.append((cur_time, cur_info))

        if cur_info.total_recv < prev_info.total_recv:
            recv_overflows += 1

        if cur_info.total_sent < prev_info.total_sent:
            send_overflows += 1

        dt = cur_time - comp_time
        yield TrafficInfo(
            cur_info.total_recv - start_info.total_recv + (recv_overflows<<32),
            cur_info.total_sent - start_info.total_sent + (send_overflows<<32),
            (cur_info.total_recv - comp_info.total_recv) / dt,
            (cur_info.total_sent - comp_info.total_sent) / dt)



def format_rate(num_bytes):
    return "{:5.1f}".format(num_bytes*8.0/1024**2) + " Mbit/s"


def format_size(num_bytes):
    return "{:5.1f}".format(num_bytes*1.0/1024**2) + " MiB"


def main():
    for ti in monitor_traffic(0.1, 30):
        _clear_line(sys.stdout)
        print('R:', format_rate(ti.rate_recv),
              '    S:', format_rate(ti.rate_send),
              '   TR:', format_size(ti.total_recv),
              '   TS:', format_size(ti.total_sent),
              end='')
        sys.stdout.flush()


if __name__ == "__main__":
    main()
