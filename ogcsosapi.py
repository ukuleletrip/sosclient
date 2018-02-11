#! /usr/bin/env python
# -*- coding:utf-8 -*-
"""OGC SOS API module

This module allows SOS client developer to use SOS API easily.
It provides SOSServer class and functions to use SOS API.

"""
from __future__ import print_function

__version__ = '1.0'
__author__ = 'Satoru MIYAMOTO'
__date__ = '2017-01-19'
__license__ = 'MIT'

import sys
if sys.version_info[0] == 2:
    from HTMLParser import HTMLParser
    from urllib2 import urlopen, Request, HTTPError
else:
    from html.parser import HTMLParser
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
import copy
from io import StringIO
from datetime import datetime, timedelta, tzinfo
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring, fromstring, ParseError
import time

ISO8601_NO_TZ = '%Y-%m-%dT%H:%M:%S'
ISO8601_JST = '%Y-%m-%dT%H:%M:%S+0900'

debug=False

class LocalTimezone(tzinfo):
    def utcoffset(self, dt):
        return timedelta(seconds=-time.timezone)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return time.tzname[0]


def parse_iso8601_datetime(dt_str):
    elms = dt_str.split('+')
    return datetime.strptime(elms[0], ISO8601_NO_TZ)
    

def get_namespaces(xmlfile):
    """read namespace definitions from XML file's root tag.

    if you want to know why this is needed, please read
      http://effbot.org/zone/element-namespaces.htm

    Args:
      xmlfile (file object): xmlfile

    Returns:
      dict: has qname as key and URI as value
      {'xmlns:fes' : 'http://www.opengis.net/fes/2.0',
       'xmlns:gml' : 'http://www.opengis.net/gml/3.2'}

    """
    events = "start", "start-ns"
    namespaces = {}
    for event, elem in ET.iterparse(xmlfile, events):
        if event == "start-ns":
            namespaces[elem[0]] = elem[1]
        elif event == "start":
            break
    return namespaces

def get_cn_tag(path, namespaces):
    """convert qname to clark notation in specified XPath

    Args:
      path (str): XPath
      path (dict): namespace dictionary such as get_namespaces creates

    Returns:
      str: converted XPath

    """
    tags = path.split('/')
    cn_tags = []
    for tag in tags:
        elems = tag.split(':')
        if len(elems) == 2 and elems[0] in namespaces:
            cn_tags.append('{' + namespaces[elems[0]] + '}' + elems[1])
        else:
            cn_tags.append(tag)

    return '/'.join(cn_tags)


def default_ogc_namespaces():
    """return default OGC namespaces

    the namespaces are described in Table12 in p.8 of
    "OGC Sensor Observation Service Interface Standard" Version 2.0

    Returns:
      dict: has qname as key and URI as value

    """
    ns = {
        'xmlns:fes' : 'http://www.opengis.net/fes/2.0',
        'xmlns:gml' : 'http://www.opengis.net/gml/3.2',
        'xmlns:om'  : 'http://www.opengis.net/om/2.0',
        'xmlns:ows' : 'http://www.opengis.net/ows/1.1',
        'xmlns:sos' : 'http://www.opengis.net/sos/2.0',
        'xmlns:swe' : 'http://www.opengis.net/swe/2.0',
        'xmlns:swes': 'http://www.opengis.net/swes/2.0',
        'xmlns:ogc' : 'http://www.opengis.net/ogc',
        'xmlns:wsa' : 'http://www.w3.org/2005/08/addressing',
        'xmlns:xs'  : 'http://www.w3.org/2001/XMLSchema',
        'xmlns:xsi' : 'http://www.w3.org/2001/XMLSchema-instance',
        'xmlns:xlink'        : 'http://www.w3.org/1999/xlink', 
        'xsi:schemaLocation' : 'http://www.opengis.net/sos/2.0'
                               ' http://schemas.opengis.net/sos/2.0/sos.xsd',
    }
    return ns


class Server(object):
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


class Provider(object):
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


class Observation(object):
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


class Measurement(object):
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


def parse_offering(offering, namespaces):
    observation_offering = offering.find(get_cn_tag('sos:ObservationOffering', namespaces))
    observation = Observation()
    observation.properties = []
    for child in observation_offering:
        if child.tag.endswith('}description'):
            observation.description = child.text
        elif child.tag.endswith('}name'):
            observation.name = child.text
        elif child.tag.endswith('}procedure'):
            observation.procedure = child.text
        elif child.tag.endswith('}observableProperty'):
            observation.properties.append(child.text)
    return observation


def parse_service(service, namespaces):
    server = Server()
    for child in service:
        if child.tag.endswith('}Title'):
            server.name = child.text
        elif child.tag.endswith('}ServiceType'):
            server.service_type = child.text
        elif child.tag.endswith('}ServiceTypeVersion'):
            server.service_version = child.text
        elif child.tag.endswith('}Fees'):
            server.fees = child.text
    return server


def parse_provider(provider_, namespaces):
    provider = Provider()
    for child in provider_:
        if child.tag.endswith('}ProviderName'):
            provider.name = child.text
        elif child.tag.endswith('}ServiceContact'):
            provider.indiviual_name = child.find(get_cn_tag('ows:IndividualName',
                                                            namespaces)).text
            provider.posision_name = child.find(get_cn_tag('ows:PositionName', namespaces)).text
            adr = child.find(get_cn_tag('ows:ContactInfo/ows:Address', namespaces))
            provider.point = adr.find(get_cn_tag('ows:DeliveryPoint', namespaces)).text
            provider.city = adr.find(get_cn_tag('ows:City', namespaces)).text
            provider.pref = adr.find(get_cn_tag('ows:AdministrativeArea', namespaces)).text
            provider.country = adr.find(get_cn_tag('ows:Country', namespaces)).text

    return provider


def parse_observation(observation, namespaces):
    time = observation.find(get_cn_tag('om:phenomenonTime/gml:TimeInstant/gml:timePosition',
                                       namespaces)).text
    dt = parse_iso8601_datetime(time)
    result = observation.find(get_cn_tag('om:result', namespaces))
    return (dt, observation.find(get_cn_tag('om:observedProperty',
                                            namespaces)).text.strip('"'),
            dict(value=float(result.text),
                 uom=HTMLParser().unescape(result.attrib['uom'])))


def parse_operations(operations_root, namespaces):
    oplist = operations_root.findall(get_cn_tag('ows:Operation', namespaces))
    operations = []
    for op in oplist:
        operations.append(op.attrib['name'])

    return operations


def _build_get_data_request(procedure, properties, time_range, operation, namespaces):
    attrib = copy.deepcopy(namespaces)
    attrib['service'] = 'SOS'
    attrib['version'] = '2.0.0'
    root = Element('sos:%s' % (operation), attrib)
    SubElement(root, 'sos:offering').text = procedure

    for prop in properties:
        SubElement(root, 'sos:observedProperty').text = prop

    temporal_filter = SubElement(root, 'sos:temporalFilter')
    if len(time_range) == 2:
        # start and end
        during = SubElement(temporal_filter, 'fes:During')
        SubElement(during, 'fes:ValueReference').text = 'phenomenonTime'
        time_period = SubElement(during, 'gml:TimePeriod', {'gml:id' : 't1'})
        SubElement(time_period, 'gml:beginPosition').text = time_range[0].strftime(ISO8601_JST)
        SubElement(time_period, 'gml:endPosition').text = time_range[1].strftime(ISO8601_JST)
    else:
        equals = SubElement(temporal_filter, 'fes:TEquals')
        SubElement(equals, 'fes:ValueReference').text = 'phenomenonTime'
        time_instant = SubElement(equals, 'gml:TimeInstant', {'gml:id' : 't1'})
        if len(time_range) == 1:
            SubElement(time_instant, 'gml:timePosition').text = time_range[0].strftime(ISO8601_JST)
        else:
            SubElement(time_instant, 'gml:timePosition').text = 'last'

    return root


def build_get_observation_request(procedure, properties, time_range, namespaces):
    """builds request XML for GetObservation.

    Args:
      procedure (str): SOSName, procedure. ex. 'TEST:Field:SensorNodeName'
      properties (list): list of observed properties. (str) ex. 'air_temperature'
      time_range (list): has 2 datetime object, start time and end time.
      namespaces (dict): has qname as key and URI as value, represents namespaces for XML

    Returns:
      Element object: represents request XML

    """
    return _build_get_data_request(procedure, properties, time_range,
                                   'GetObservation', namespaces)


def build_get_result_request(procedure, properties, time_range, namespaces):
    """builds request XML for GetReult.

    Args:
      procedure (str): SOSName, procedure. ex. 'TEST:Field:SensorNodeName'
      properties (list): list of observed properties. (str) ex. 'air_temperature'
      time_range (list): has 2 datetime object, start time and end time.
      namespaces (dict): has qname as key and URI as value, represents namespaces for XML

    Returns:
      Element object: represents request XML

    """
    return _build_get_data_request(procedure, properties, time_range,
                                   'GetResult', namespaces)


def build_get_capabitilies_request(namespaces):
    """builds request XML for GetCapabilities.

    Args:
      namespaces (dict): has qname as key and URI as value, represents namespaces for XML

    Returns:
      Element object: represents request XML

    """
    attrib = copy.deepcopy(namespaces)
    # it is weird that we cannot use sos namespace for GetCapabilities
    attrib['xmlns'] = attrib['xmlns:sos']
    attrib['service'] = 'SOS'
    root = Element('GetCapabilities', attrib)

    ows_accept_version = SubElement(root, 'ows:AcceptVersion')
    SubElement(ows_accept_version, 'ows:Version').text = '2.0.0'
    ows_sections = SubElement(root, 'ows:Sections')
    sections = ['OperationsMetadata',
                'ServiceIdentification',
                'ServiceProvider',
                'Filter_Capabilities',
                'Contents']
    for section in sections:
        SubElement(ows_sections, 'ows:Section').text = section

    return root


def build_insert_observation_request(procedure, measurements, namespaces):
    """builds request XML for InsertObservation.

    Args:
      procedure (str): SOSName, procedure. ex. 'TEST:Field:SensorNodeName'
      measurements (dict): has a datetime object as key and
                           its value (dict) has a property as key and
                           its value (dict) has a dict which has 'value' and 'uom'.
      namespaces (dict): has qname as key and URI as value, represents namespaces for XML

    Returns:
      Element object: 

    """
    attrib = copy.deepcopy(namespaces)
    attrib['service'] = 'SOS'
    attrib['version'] = '2.0.0'
    root = Element('sos:InsertObservation', attrib)
    SubElement(root, 'sos:offering').text = procedure
    #SubElement(root, 'swe:responseFormat').text = 'JSON_WITH_CONSTANTS'

    for dt in measurements:
        for prop in measurements[dt]:
            observation = SubElement(root, 'sos:observation')
            om_observation = SubElement(observation, 'om:OM_Observation', { 'gml:id': 'obsTest1' })
            SubElement(om_observation, 'om:type',
                       { 'xlink:hrel': 'http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_Measurement' })
            phenomenon_time = SubElement(om_observation, 'om:phenomenonTime')
            time_instant = SubElement(phenomenon_time, 'gml:TimeInstant',
                                      { 'gml:id': 'phenomenonTime' })
            SubElement(time_instant, 'gml:timePosition').text = dt.strftime(ISO8601_JST)
            SubElement(om_observation, 'om:resultTime', { 'xlink:href': '#phenomenonTime' })
            SubElement(om_observation, 'om:procedure').text = procedure
            SubElement(om_observation, 'sos:observedProperty').text = prop
            SubElement(om_observation, 'om:result', { 'xsi:type': 'gml:MeasureType',
                                                      'uom'     : measurements[dt][prop]['uom'] }
            ).text = measurements[dt][prop]['value']
    
    return root


def call_ogc_api(url, req_body, token=None, token_param=None):
    """call ogc API

    Args:
      url (str): URL of API, including Token in parameter.
      req_body (str): request body, XML string

    Returns:
      (Element, dict): 1st returned Element is a response body XML tree.
                       2nd returned dict is namespace dictionary from response.

    """
    if debug:
        print(req_body)

    if type(req_body) == bytes:
        pass
    else:
        req_body = req_body.encode('utf-8')

    headers = {'content-type' : 'application/xml; charset="utf-8"'}
    if 'header' in url:
        headers.update(url['header'])
    req = Request(url['url'],
                  req_body,
                  headers)
    try:
        resp = urlopen(req)
    except HTTPError as e:
        print(e.code, e.reason)
        print(e.read())
        raise
        return '<HTTPError><Code>{}</Code><Reason>{}</Reason></HTTPError>' \
            .format(e.code, e.reason), None
        
    resp_body = resp.read()

    if debug:
        print(resp_body)

    try:
        namespaces = get_namespaces(StringIO(resp_body.decode('utf-8')))
        return fromstring(resp_body), namespaces
    except ParseError:
        # some response seems to be illegal.
        return resp_body, None


def get_capabilities(url):
    """execute GetCapabilities operation.

    Args:
      url (str): URL of API, including Token in parameter.

    Returns:
      (Server, Provider, list of Operation (str), list of Filter (str), list of Observation)

    Examples:
      (server, provider, operations, filters, observations) = \
            get_capabilities('https://sos.foo.com/api?Key=xxxxxx')

    """
    req = build_get_capabitilies_request(default_ogc_namespaces())
    (resp_root, namespaces) = call_ogc_api(url, tostring(req, 'utf-8'))

    server = parse_service(resp_root.find(get_cn_tag('ows:ServiceIdentification', namespaces)),
                           namespaces)

    provider = parse_provider(resp_root.find(get_cn_tag('ows:ServiceProvider', namespaces)),
                              namespaces)

    operations = parse_operations(resp_root.find(get_cn_tag('ows:OperationsMetadata', namespaces)),
                                  namespaces)

    filters = []
    #filters = resp_root.find(get_cn_tag('sos:filterCapabilities', namespaces))
    #self.filters = self.parse_filters(filters, namespaces)

    offerings = resp_root.findall(get_cn_tag('sos:contents/sos:Contents/swes:offering',
                                             namespaces))
    observations = []
    for offering in offerings:
        observations.append(parse_offering(offering, namespaces))

    return server, provider, operations, filters, observations


def get_observation(url, procedure, properties, time_range):
    """execute GetObservation operation.

    Args:
      url (str): URL of API, including Token in parameter.
      procedure (str): SOSName, procedure. ex. 'TEST:Field:SensorNodeName'
      properties (list): list of observed properties. (str) ex. 'air_temperature'
      time_range (list): has 2 datetime object, start time and end time.

    Returns:
      dict: has datetime object as key and result (dict) as value.
            result (dict) has observed property as key and value (dict) as value.
            value (dict) has 'value' (value)  and 'uom' (unit name)

    Examples:
      measurements = get_observation('https://sos.foo.com/api?Key=xxxxxx',
                                 'TEST:Field:SensorNodeName',
                                 ['air_temperature', 'relative_humidity'],
                                 [datetime(2017, 1, 1, 0, 0, 0), datetime(2017, 1, 1, 0, 5, 0)])
    """
    req = build_get_observation_request(procedure, properties, time_range,
                                        default_ogc_namespaces())
    (resp_root, namespaces) = call_ogc_api(url, tostring(req, 'utf-8'))
    observations = resp_root.findall(get_cn_tag('sos:observationData/om:OM_Observation',
                                                namespaces))
    measurements = {}
    for observation in observations:
        (dt, prop, value) = parse_observation(observation, namespaces)
        if dt not in measurements:
            measurements[dt] = {}
        measurements[dt][prop] = value

    return measurements


def get_result(url, procedure, properties, time_range):
    """execute GetResult operation.

    Args:
      url (str): URL of API, including Token in parameter.
      procedure (str): SOSName, procedure. ex. 'TEST:Field:SensorNodeName'
      properties (list): list of observed properties. (str) ex. 'air_temperature'
      time_range (list): has 2 datetime object, start time and end time.

    Returns:
      dict: has datetime object as key and result (dict) as value.
            result (dict) has observed property as key and value (dict) as value.
            value (dict) has 'value' (value)  and 'uom' (unit name)

    Note:
      cloudSense SOS server accepts multiple observed properties for GetResult,
      but in the specification it is not allowed.

    Examples:
      measurements = get_result('https://sos.foo.com/api?Key=xxxxxx',
                                'TEST:Field:SensorNodeName',
                                ['air_temperature', 'relative_humidity'],
                                [datetime(2017, 1, 1, 0, 0, 0), datetime(2017, 1, 1, 0, 5, 0)])

    """
    req = build_get_result_request(procedure, properties, time_range,
                                   default_ogc_namespaces())
    (resp_root, namespaces) = call_ogc_api(url, tostring(req, 'utf-8'))
    results = resp_root.find(get_cn_tag('sos:resultValues',
                                        namespaces)).text.strip().split('\n')

    measurements = {}
    prop_idx = 0
    prev_dt = None
    for l in results:
        elem = l.split(',')
        if len(elem) == 2:
            dt = parse_iso8601_datetime(elem[0])
            value = {'value' : float(elem[1]), 'uom' : ''}

            if prev_dt and dt < prev_dt:
                # next prop
                prop_idx += 1

            prop = properties[prop_idx]
            if dt not in measurements:
                measurements[dt] = {}
            measurements[dt][prop] = value
            prev_dt = dt

    return measurements

def insert_observation(url, procedure, measurements):
    req = build_insert_observation_request(procedure, measurements, default_ogc_namespaces())
    (resp_root, namespaces) = call_ogc_api(url, tostring(req, 'utf-8'))
    # <sos:InsertObservationResponse>
    #   <sos:observation>Inserted</sos:observation>
    # </sos:InsertObservationResponse>
    # but, it should be
    # <sos:InsertObservationResponse xmlns:sos="http://www.opengis.net/sos/2.0">
    #   <sos:observation>Inserted</sos:observation>
    # </sos:InsertObservationResponse>
    if namespaces is None:
        # illegal response
        result = resp_root
    else:
        result = resp_root.find(get_cn_tag('sos:observation', namespaces)).text
    return result


class SOSServer(object):
    """a class represents SOS Server.

    Current version assumes a token is specified by '?Key=' URL parameter.
    Future version will support more ways to specify a token.

    Args:
      endpoint (str): SOS API endpoint on the server
      token (str): Token to use SOS API on the server

    Examples:
      server = SOSAPI('https://sos.foo.com/api', 'XXXXXXXX')
      results = server.get_observation('TESTDEV:Field:Sensor',
                                       ['air_temperature', 'water_temperature'],
                                       [datetime(2017, 1, 1, 0, 0, 0),
                                        datetime(2017, 1, 1, 0, 10, 0)])
      for dt, measure in sorted(results.items()):
        for prop in measure:
          print measure[prop]['value']

    """

    def __init__(self, endpoint, token, is_token_header=False):
        self.endpoint = endpoint
        self.token = token
        self.server = None
        self.provider = None
        self.operations = []
        self.filters = []
        self.observations = []
        self.is_token_header = is_token_header

    @staticmethod
    def _get_procedure(offering):
        return offering if type(offering) == str else offering.procedure

    def _get_api_url(self):
        if not self.is_token_header and self.token:
            return { 'url' : '%s?Key=%s' % (self.endpoint, self.token) }
        else:
            return { 'url'    : self.endpoint,
                     'header' : { 'Authorization' : self.token } }

    def get_capabilities(self):
        """execute GetCapabilities operation in context of the SOSServer instance.

        Returns:
          (Server, Provider, list of Operation (str), list of Filter (str), list of Observation)

        """
        return get_capabilities(self._get_api_url())


    def get_observation(self, offering, properties, time_range):
        """execute GetObservation operation in context of the SOSServer instance.

        Args:
          offering (Observation object/str): observation offering (sensor node)
                                             if offering is str, it is treated as
                                             SOSName, procedure.
          properties (list): list of observed properties. (str) ex. 'air_temperature'
          time_range (list): has 2 datetime object, start time and end time.

        Returns:
          dict: has datetime object as key and result (dict) as value.
                result (dict) has observed property as key and value (dict) as value.
                value (dict) has 'value' (value)  and 'uom' (unit name)
        """
        return get_observation(self._get_api_url(),
                               self._get_procedure(offering),
                               properties, time_range)


    def get_result(self, offering, properties, time_range):
        """execute GetResult operation in context of the SOSServer instance.

        Args:
          offering (Observation object/str): observation offering (sensor node)
                                             if offering is str, it is treated as
                                             SOSName, procedure.
          properties (list): list of observed properties. (str) ex. 'air_temperature'
          time_range (list): has 2 datetime object, start time and end time.

        Returns:
          dict: has datetime object as key and result (dict) as value.
                result (dict) has observed property as key and value (dict) as value.
                value (dict) has 'value' (value)  and 'uom' (unit name)

        Note:
          cloudSense SOS server accepts multiple observed properties for GetResult,
          but in the specification it is not allowed.

        """
        return get_result(self._get_api_url(),
                          self._get_procedure(offering),
                          properties, time_range)


    def insert_observation(self, offering, measurements):
        return insert_observation(self._get_api_url(),
                                  self._get_procedure(offering),
                                  measurements)


    def update_capabilities(self):
        """execute GetCapabilities operation and holds its result in the instance.
           
          This updates server, provider, operations, filters, observations of the instance.

        """
        (self.server,
         self.provider,
         self.operations,
         self.filters,
         self.observations) = self.get_capabilities()


if __name__ == '__main__':
    pass
