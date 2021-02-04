"""Helper functions that get output via netmiko"""

import collections
import ipaddress
import string
import app.Modules.GetInterfaces as GetInterfacesInfo
import app.Modules.connection as ConnectWith
import app.base.routes as Credentials
from netmiko import ConnectHandler, ssh_exception
import time


def send_command(netmiko_connection, command, expect_string=None):
    """Send Netmiko commands"""

    netmiko_connection = netmiko_connection
    get_response = None

    if expect_string is None:

        retries = 0
        while retries != 3:
            try:
                get_response = netmiko_connection.send_command(command)
                break
            except (OSError, TypeError, AttributeError, ssh_exception.NetmikoTimeoutException):
                netmiko_connection = ConnectWith.creat_netmiko_connection(Credentials.username, Credentials.password,
                                                                          Credentials.device, Credentials.ssh_port)
                Credentials.netmiko_session = netmiko_connection
                retries += 1

    else:

        retries = 0
        while retries != 3:
            try:
                get_response = netmiko_connection.send_command(command, expect_string=expect_string)
                break
            except (OSError, TypeError, AttributeError, ssh_exception.NetmikoTimeoutException):
                netmiko_connection = ConnectWith.creat_netmiko_connection(Credentials.username, Credentials.password,
                                                                          Credentials.device, Credentials.ssh_port)
                retries += 1

    if retries == 3:
        get_response = 'Error Connecting'

    return get_response


def more_int_details(netmiko_session, interface, vdc=None):

    if vdc is not None:
        vdc_command = f"switchto vdc {vdc}"
        get_vdcs = send_command(netmiko_session, vdc_command)

    get_more_details = send_command(netmiko_session, f'show interface {interface}')

    return get_more_details


def get_arp(netmiko_session, vdc=None):
    """Get ARP table"""

    arps = []
    if vdc is not None:
        vdc_command = f"switchto vdc {vdc}"
        get_vdcs = send_command(netmiko_session, vdc_command)

    get_arps = send_command(netmiko_session, 'show ip arp | begin Address')

    if get_arps:
        for i in get_arps.splitlines():
            try:
                if i.split()[0] != 'Address':
                    arps.append({'ip': i.split()[0], 'age': i.split()[1],
                         'mac': i.split()[2], 'interface': i.split()[3]})
            except IndexError:
                pass
    else:
        return 'An Error Occured'

    return arps


def get_vdcs(netmiko_session):
    """Using the connection object created from the netmiko_login(), get vdcs"""

    vdcs = []
    vdc_command = "show vdc detail"
    get_vdcs = send_command(netmiko_session, vdc_command)
    vdc_current_command = "show vdc current-vdc"
    get_current_vdc = send_command(netmiko_session, vdc_current_command)
    lines = get_vdcs.split("\n")

    for line in lines:
        if line.rfind("vdc name") != -1:
            vdc = line.split()[2]
            vdcs.append(vdc)
        else:
            pass
    
    return vdcs, get_current_vdc.split()[5]


def switch_vdc(netmiko_connection, vdc):
    """Using the connection object created from the netmiko_login(), get vdcs"""

    vdcs = []
    vdc_command = f"switchto vdc {vdc}"
    get_vdcs = send_command(netmiko_connection, vdc_command, expect_string='')
    terminal_command = f"terminal length 0"
    get_vdcs = send_command(netmiko_connection, terminal_command, expect_string='')

def switch_vdc_back(netmiko_connection):
    """Using the connection object created from the netmiko_login(), get vdcs"""

    vdcs = []
    vdc_command = f"switchback"
    get_vdcs = send_command(netmiko_connection, vdc_command, expect_string='')
    time.sleep(3)

def get_span_root(netmiko_session, vdc=None) -> list:
    """Get spanning tree"""

    span_table = []
    if vdc is not None:
        vdc_command = f"switchto vdc {vdc}"
        get_vdcs = send_command(netmiko_session, vdc_command)

    get_macs = 'show spanning-tree root'
    table = send_command(netmiko_session, get_macs)

    for vlan in table.splitlines():
        try:
            if vlan.split()[0].rfind("-") != -1:
                continue
            elif vlan.split()[0] == 'Vlan':
                continue
            else:
                if vlan.split()[0][-2] == "0":

                    if len(vlan.split()) == 8:
                        span_table.append(
                            {'vlan': vlan.split()[0][-1:], 'root-prio': vlan.split()[1], 'root-id': vlan.split()[2],
                             'root-cost': vlan.split()[3], 'root-port': vlan.split()[7]})
                    elif len(vlan.split()) == 7:
                        span_table.append(
                            {'vlan': vlan.split()[0][-1:], 'root-prio': vlan.split()[1], 'root-id': vlan.split()[2],
                             'root-cost': vlan.split()[3], 'root-port': "Root Bridge"})
                else:

                    if len(vlan.split()) == 8:
                        span_table.append(
                            {'vlan': vlan.split()[0][-2:], 'root-prio': vlan.split()[1], 'root-id': vlan.split()[2],
                             'root-cost': vlan.split()[3], 'root-port': vlan.split()[7]})
                    elif len(vlan.split()) == 7:
                        span_table.append(
                            {'vlan': vlan.split()[0][-1:], 'root-prio': vlan.split()[1], 'root-id': vlan.split()[2],
                             'root-cost': vlan.split()[3], 'root-port': "Root Bridge"})
        except IndexError:
            continue

    return span_table


def get_mac_table(netmiko_session, vdc=None):
    """Get mac-address-table"""

    mac_table = []
    get_macs = 'show mac address-table'

    if vdc is not None:
        vdc_command = f"switchto vdc {vdc}"
        get_vdcs = send_command(netmiko_session, vdc_command)

    table = send_command(netmiko_session, get_macs)

    for mac in table.splitlines():
        try:
            if mac.split()[0].rfind("-") != -1:
                continue
            elif mac.split()[0] == 'Vlan':
                continue
            elif mac.split()[0] == 'All':
                continue
            elif mac.split()[0] == 'Total':
                continue
            else:
                mac_table.append({'vlan': mac.split()[1], 'address': mac.split()[2], 'type': mac.split()[3],
                                  'interface': mac.split()[7]})
        except IndexError:
            continue

    return mac_table


def get_vlans(netmiko_session, vdc=None) -> list:
    """Get vlans"""

    vlan_table = []
    iter_vlan = "1"
    ports = ['']

    if vdc is not None:
        vdc_command = f"switchto vdc {vdc}"
        get_vdcs = send_command(netmiko_session, vdc_command)

    get_vlans = 'show vlan brief'
    vlan_ports = None

    vlans = send_command(netmiko_session, get_vlans, expect_string='')

    cli_line = vlans.split("\n")
    for line in cli_line:
        if not list(enumerate(line.split(), 0)):
            continue
        if line.split()[0] == "VLAN":
            continue
        if line.split()[0].rfind("-") != -1:
            continue
        if '/' in line.split()[0]:
            ports = line.split()[0:]
        else:
            vlan_table.append({'id': line.split()[0], 'name': line.split()[1], 'ports': " ".join(line.split()[3:] + ports)})

    return vlan_table


def get_trunks(netmiko_session, vdc=None) -> list:
    """Get trunks"""

    trunks = {}

    if vdc is not None:
        vdc_command = f"switchto vdc {vdc}"
        get_vdcs = send_command(netmiko_session, vdc_command)

    trunk_command = 'show int trunk | grep ,'
    get_trunks = send_command(netmiko_session, trunk_command)

    cli_line = get_trunks.split("\n")
    for line in cli_line:
        if not list(enumerate(line.split(), 0)):
            continue
        if line.split()[0] == "Port":
            continue
        if line.split()[0][0] == 'E' or line.split()[0][0] == 'P':
            trunks[line.split()[0]] = " ".join(line.split()[1:])

    return trunks


def get_port_channels(netmiko_session, vdc=None) -> list:
    """Get port-channels"""

    port_channels = {}
    if vdc is not None:
        vdc_command = f"switchto vdc {vdc}"
        get_vdcs = send_command(netmiko_session, vdc_command)

    port_channels_command = 'show port-channel summary | begin Group'
    get_port_channels = send_command(netmiko_session, port_channels_command)

    cli_line = get_port_channels.split("\n")
    for line in cli_line:
        if not list(enumerate(line.split(), 0)):
            continue
        if line.split()[0] == "Group" or line.split()[0] == '--------------------------------------------------------------------------------' or line.split()[0] == 'Channel':
            continue
        else:
            join_ports = ", ".join(line.split()[4:])
            # port_channels[line.split()[0]] = join_ports.replace('(P)', "").replace('(D)', "")
            port_channels[f'po{line.split()[0]}'] = join_ports

    return port_channels


def get_interface_names(netmiko_session, vdc=None) -> list:
    """Get trunks"""

    interfaces = []
    if vdc is not None:
        vdc_command = f"switchto vdc {vdc}"
        get_vdcs = send_command(netmiko_session, vdc_command)

    interface_command = 'show int status'
    get_interfaces = send_command(netmiko_session, interface_command)

    cli_line = get_interfaces.split("\n")
    for line in cli_line:

        if not list(enumerate(line.split(), 0)):
            continue
        if line.split()[0] == "Port":
            continue
        else:
            try:
                interfaces.append({'interface': line.split()[0],'vlan': line.split()[3], 'status': line.split()[2], 'duplex': line.split()[4],
                                   'speed': line.split()[5], 'type': line.split()[6]})
            except IndexError:
                pass

    return interfaces


def get_vpcs(netmiko_session, vdc=None):

    vpc = []
    if vdc is not None:
        vdc_command = f"switchto vdc {vdc}"
        get_vdcs = send_command(netmiko_session, vdc_command)

    vpc_command = ' show vpc  | beg Id | ex Please | ex consis | ex any '
    get_vpcs = send_command(netmiko_session, vpc_command)

    cli_line = get_vpcs.split("\n")
    for line in cli_line:

        if not list(enumerate(line.split(), 0)):
            continue
        if line.split()[0] == "--":
            continue
        if line.split()[0] == "Id":
            continue
        else:
            try:
                vpc.append({'id': line.split()[0], 'port': line.split()[1], 'status': line.split()[2], 'consistancy': line.split()[3],
                                   'reason': line.split()[4], 'active_vlans': line.split()[5]})
            except IndexError:
                pass

    return vpc
