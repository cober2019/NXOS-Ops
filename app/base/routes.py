# -*- encoding: utf-8 -*-

from flask import jsonify, render_template, redirect, request, url_for, flash
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user
)
from app import db, login_manager
from app.base import blueprint
from app.base.forms import LoginForm
import string
from app.base.models import User
from app.base.util import verify_pass
from app.Modules.ProjectRouting.Software import NXOS
import app.Modules.ProjectRouting.Database.DB_queries as Db_queries
import app.Modules.ProjectRouting.Database.DatabaseOps as DB
import app.Modules.connection as ConnectWith
import app.Modules.GetInterfaces as GetInterfacesInfo
import app.Modules.GetWithNetmiko as GetInfo
import app.Modules.InterfacesQoS as GetQos
import app.Modules.bgp_build as Build_bgp_config
import app.Modules.ospf_build as Build_ospf_config
import app.Modules.netconfsend as SendConfig
import app.Modules.AsrListlist as GetPolicies
import app.Modules.build_service_policy as BuildService
import app.Modules.interface_build as BuildInterface
import sqlite3
import logging
import os

device = None
username = None
password = None
ssh_port = None
netmiko_session = None
vlans = None
trunks = None
port_channels = None
interfaces = None
vdcs = None
vdc = None

log_dir = os.path.dirname(os.path.realpath(__file__)).replace('base', 'logs\\')
logging.basicConfig(filename=f'{log_dir}sessionlog.log', level=logging.INFO)


@blueprint.route('/')
def route_default():
    return redirect(url_for('base_blueprint.login'))


@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    global device, username, password, netconf_session, netmiko_session, model, netconf_port, ssh_port, vdcs

    login_form = LoginForm(request.form)
    if 'login' in request.form:

        device = request.form['device']
        username = request.form['username']
        password = request.form['password']
        ssh_port = request.form['ssh']

        if not ssh_port:
            ssh_port = 22

        if device and username and password:

            # Attempt to create connection objects. Must have both to get to homepage
            netmiko_session = ConnectWith.creat_netmiko_connection(request.form['username'], request.form['password'],
                                                                   request.form['device'], ssh_port)

            # Using netmiko and ncclient for connections, verify that both pass. If one fails, return to login
            if netmiko_session == 'Authenitcation Error':
                flash("Authentication Failure")
                return redirect(url_for('base_blueprint.login'))
            elif netmiko_session == 'ssh_exception' or netmiko_session == 'Connection Timeout':
                flash("Check Device Connectivity")
                return redirect(url_for('base_blueprint.login'))
            else:
                return redirect(url_for('base_blueprint.layer_2'))

        return render_template('accounts/login.html', msg='Wrong user or password', form=login_form)

    if not current_user.is_authenticated:
        return render_template('accounts/login.html',
                               form=login_form)
    return redirect(url_for('home_blueprint.index'))


@blueprint.route('/logout')
def logout():
    """User logout and re-login"""

    logout_user()
    return redirect(url_for('base_blueprint.login'))


@blueprint.route('/routing', methods=['POST'])
def table_refresh():
    """Used for table refreshes"""

    action = request.form.get('action')

    # Used for refreshing tables without page reload, return data to call wich is js/ajax
    if action == 'arp':
        clear = GetInfo.clear_arp(netmiko_session)
        return jsonify({'data': render_template('refresh_arp.html', arps=clear)})
    elif action == 'bgp':
        get_status = GetInfo.get_bgp_status(netmiko_session)
        return jsonify({'data': render_template('refresh_bgp.html', bgp=get_status[0])})
    elif action == 'ospf':
        get_status = GetInfo.get_ospf_status(netmiko_session)
        return jsonify({'data': render_template('refresh_ospf.html', ospf=get_status)})
    elif action == 'clearInt':
        clear = GetInfo.clear_counters(netmiko_session, request.form.get('interface'), netconf_session)
        return jsonify({'data': render_template('refresh_table.html', interfaces=clear)})
    elif action == 'mac':
        mac_to_arp = GetInfo.get_mac_arp_table(netmiko_session)
        return jsonify({'data': render_template('refresh_mac.html', mac_arp=mac_to_arp)})
    elif action == 'cdp':
        cdp =GetInfo.get_cdp_neighbors(netmiko_session)
        return jsonify({'data': render_template('refresh_cdp.html', neighbors=cdp)})
    elif action == 'access':
        access_ports = GetInterfacesInfo.get_access_ports(netconf_session)
        return jsonify({'data': render_template('refresh_access.html', access_ports=access_ports)})
    elif action == 'span':
        spanning_tree = GetInfo.get_span_root(netmiko_session)
        return jsonify({'data': render_template('refresh_span.html', roots=spanning_tree)})


@blueprint.route('/int_details', methods=['POST'])
def interface_details():
    """Used for table refreshes"""

    int_details = GetInfo.more_int_details(netmiko_session, request.form.get('details'))

    return render_template('more_int_detials.html', details=int_details)


@blueprint.route('/modify_inteface/<interface>')
def modify_inteface(interface):
    """POST BGP configuration from form data"""

    reformat_interface = interface.replace('%2f', '/')

    return render_template('modify_interface.html', interface=reformat_interface, vlans=vlans)


@blueprint.route('/modify_inteface', methods=['POST'])
def submit_inteface():
    """POST interface configuration from form data"""

    status = None
    descr = None
    int_num = [i for i in request.form.get("interface") if i not in string.ascii_letters]
    int_type = [i for i in request.form.get("interface") if i in string.ascii_letters]
    interface = BuildInterface.Templates(''.join(int_type), ''.join(int_num))

    interface = request.form.get('interface')
    vlan_id = request.form.get('vlanId')
    print(interface)
    print(vlan_id)

    if request.form.get('status'):
        status = request.form.get('status')
        print(status)

    # Your config functions goes here, pass vlan variable from form

    return redirect(url_for('base_blueprint.layer_2'))


@blueprint.route('/layer2')
def layer_2():
    """Gets layer two information from the device"""

    global vdcs

    vlans = GetInfo.get_vlans(netmiko_session)
    trunks = GetInfo.get_trunks(netmiko_session)
    port_channels = GetInfo.get_port_channels(netmiko_session)
    interfaces = GetInfo.get_interface_names(netmiko_session)
    arp = GetInfo.get_arp(netmiko_session)
    vdcs = GetInfo.get_vdcs(netmiko_session)
    vpcs = GetInfo.get_vpcs(netmiko_session)

    return render_template('get_layer_two.html', vlans=vlans, trunks=trunks, port_channels=port_channels,
                           interfaces=interfaces, arp=arp, vdcs=vdcs[0], current_vdc=vdcs[1], vpcs=vpcs)


@blueprint.route('/vdc_layer2', methods=['POST'])
def vdc_layer_2():
    """Gets layer two information from the device"""

    global vdc

    if vdc == None:
        vdc = request.form.get("vdc")
        GetInfo.switch_vdc(netmiko_session, vdc=request.form.get("vdc"))
    else:
        GetInfo.switch_vdc_back(netmiko_session)

    GetInfo.switch_vdc(netmiko_session, vdc=request.form.get("vdc"))
    vlans = GetInfo.get_vlans(netmiko_session)
    trunks = GetInfo.get_trunks(netmiko_session)
    port_channels = GetInfo.get_port_channels(netmiko_session)
    interfaces = GetInfo.get_interface_names(netmiko_session)
    arp = GetInfo.get_arp(netmiko_session)
    current_vdc = GetInfo.get_vdcs(netmiko_session)
    vpcs = GetInfo.get_vpcs(netmiko_session)

    return render_template('get_layer_two.html', vlans=vlans, trunks=trunks, port_channels=port_channels,
                           interfaces=interfaces, arp=arp, vdcs=vdcs[0], current_vdc=current_vdc[1], vpc=vpcs)


@blueprint.route('/all_new_form')
def add_complete():
    """Gets layer two information from the device"""

    return render_template('all_new_form.html', access_interfaces=interfaces, trunks=trunks, vlans=vlans)


@blueprint.route('/all_new_form', methods=['POST'])
def submit_complete():
    """Gets layer two information from the device"""

    vlan = request.form.get('vlanId')
    vlan_name = request.form.get('vlanName')
    vlan_descr = request.form.get('vlanDescription')
    trunk_interface = request.form.get('trunkInterface')
    access_interface = interface = request.form.get('accessInterface')

    print(vlan)
    print(vlan_name)
    print(vlan_descr)
    print(trunk_interface)
    print(access_interface)

    return redirect(url_for('base_blueprint.layer_2'))


@blueprint.route('/add_vlan')
def add_vlan():
    """Gets layer two information from the device"""

    interfaces = GetInfo.get_interface_names(netmiko_session)

    return render_template('add_vlan.html')

@blueprint.route('/add_vlan', methods=['POST'])
def submit_vlan():
    """Gets layer two information from the device"""

    vlan_id = request.form.get('vlanId')
    vlan_name = request.form.get('vlanName')
    vlan_descr = request.form.get('vlanDescription')
    
    print(vlan_id)
    print(vlan_name)
    print(vlan_descr)

    # Your config functions goes here, pass vlan variable from form

    return redirect(url_for('base_blueprint.layer_2'))


@blueprint.route('/modify_trunk_interface/<interface>')
def modify_trunk_interface(interface):
    """Gets layer two information from the device"""

    return render_template('modify_trunk_interface.html', interface=interface)

@blueprint.route('/modify_trunk_interface', methods=['POST'])
def add_vlan_to_trunk():
    """Submit new vlans to trunk"""

    interface = vlan_name = request.form.get('interface')

    if ',' in request.form.get('vlans'):
        vlan = request.form.get('vlans').split(',')
    else:
        vlan = request.form.get('vlans')
    
    print(interface)
    print(vlan)

    # Your config functions goes here, pass vlan variable from form

    return redirect(url_for('base_blueprint.layer_2'))


@blueprint.route('/modify_po_interface/<interface>')
def modify_po_interface(interface):
    """Gets layer two information from the device"""

    return render_template('modify_po_interface.html', interface='po' + interface, interfaces=interfaces)


@blueprint.route('/modify_po_interface', methods=['POST'])
def add_int_to_po():
    """Submit new vlans to trunk"""

    po_interface = vlan_name = request.form.get('poInterface')
    phys_interface = vlan_name = request.form.get('interface')

    print(po_interface)
    print(phys_interface)

    # Your config functions goes here, pass vlan variable from form

    return redirect(url_for('base_blueprint.layer_2'))


@blueprint.route('/modify_vpc_interface/<interface>')
def modify_vpc_interface(interface):
    """Gets layer two information from the device"""

    interface = f"po{interface}"

    return render_template('modify_vpc_interface.html', interface=interface, vpcs=vpcs)


@blueprint.route('/modify_vpc_interface', methods=['POST'])
def submit_vpc():
    """Submit new vlans to trunk"""

    interface = vlan_name = request.form.get('interface')
    vpc = vlan_name = request.form.get('vpcId')

    print(interface)
    print(vpc)

    # Your config functions goes here, pass vlan variable from form

    return redirect(url_for('base_blueprint.layer_2'))


@blueprint.route('/routing_table')
def routing_table():
    """Used for table refreshes"""

    routing_session = ConnectWith.creat_netmiko_connection(username, password, device, ssh_port)
    mydb = sqlite3.connect("app/Modules/ProjectRouting/Database/Routing")
    cursor = mydb.cursor()
    db_obj = DB.RoutingDatabase(mydb, cursor)
    NXOS.RoutingNexus(routing_session, db_obj, mydb, cursor)

    return render_template('get_routing.html', route_table=Db_queries.view_routes_nexus(cursor))