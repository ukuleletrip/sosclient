#! /usr/bin/env python
# -*- coding:utf-8 -*-
#
# OGC SOS API module
#
# 2017-01-19 created by S.Miyamoto@SPP
#
#

import HTMLParser
import urllib2
import copy
import StringIO
from datetime import datetime
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring, fromstring

ISO8601_FMT = '%Y-%m-%dT%H:%M:%S+0900'

# if you want to know why this is needed, please read
#   http://effbot.org/zone/element-namespaces.htm
def get_namespaces(xmlfile):
    events = "start", "start-ns"
    namespaces = {}
    for event, elem in ET.iterparse(xmlfile, events):
        if event == "start-ns":
            namespaces[elem[0]] = elem[1]
        elif event == "start":
            break
    return namespaces

def get_cn_tag(path, namespaces):
    # get clark notation tag
    tags = path.split('/')
    cn_tags = []
    for tag in tags:
        elems = tag.split(':')
        if len(elems) == 2 and elems[0] in namespaces:
            cn_tags.append('{' + namespaces[elems[0]] + '}' + elems[1])
        else:
            cn_tags.append(tag)

    return '/'.join(cn_tags)


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


class SOSServer(object):
    def __init__(self, endpoint, token):
        self.endpoint = endpoint
        self.token = token
        self.ns = SOSServer.default_ogc_namespaces()
        self.server = None
        self.provider = None
        self.operations = []
        self.filters = []
        self.observations = []

    @staticmethod
    def default_ogc_namespaces():
        # see Table12 in p.8 of
        # "OGC Sensor Observation Service Interface Standard" Version 2.0
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
            'xsi:schemaLocation' : 'http://www.opengis.net/sos/2.0'
                                   ' http://schemas.opengis.net/sos/2.0/sos.xsd',
        }
        return ns

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def parse_observation(observation, namespaces):
        time = observation.find(get_cn_tag('om:phenomenonTime/gml:TimeInstant/gml:timePosition',
                                           namespaces)).text
        dt = datetime.strptime(time, ISO8601_FMT)
        result = observation.find(get_cn_tag('om:result', namespaces))
        return (dt, observation.find(get_cn_tag('om:observedProperty',
                                                namespaces)).text.strip('"'),
                dict(value=float(result.text),
                     uom=HTMLParser.HTMLParser().unescape(result.attrib['uom'])))

    @staticmethod
    def parse_operations(operations_root, namespaces):
        oplist = operations_root.findall(get_cn_tag('ows:Operation', namespaces))
        operations = []
        for op in oplist:
            operations.append(op.attrib['name'])

        return operations

    def build_get_data_request(self, offering, properties, time_range, operation):
        attrib = copy.deepcopy(self.ns)
        attrib['service'] = 'SOS'
        attrib['version'] = '2.0.0'
        root = Element('sos:%s' % (operation), attrib)
        SubElement(root, 'sos:offering').text = offering.procedure

        for prop in properties:
            SubElement(root, 'sos:observedProperty').text = prop

        temporal_filter = SubElement(root, 'sos:temporalFilter')
        during = SubElement(temporal_filter, 'fes:During')
        SubElement(during, 'fes:ValueReference').text = 'phenomenonTime'
        time_period = SubElement(during, 'gml:TimePeriod', {'gml:id' : 't1'})
        SubElement(time_period, 'gml:beginPosition').text = time_range[0].strftime(ISO8601_FMT)
        SubElement(time_period, 'gml:endPosition').text = time_range[1].strftime(ISO8601_FMT)
        return root

    def build_get_observation_request(self, offering, properties, time_range):
        return self.build_get_data_request(offering, properties, time_range, 'GetObservation')

    def build_get_result_request(self, offering, properties, time_range):
        return self.build_get_data_request(offering, properties, time_range, 'GetResult')

    def build_get_capabitilies_request(self):
        attrib = copy.deepcopy(self.ns)
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

    def call_ogc_api(self, req_body):
        req = urllib2.Request('%s?Key=%s' % (self.endpoint, self.token),
                              req_body.encode('utf-8'),
                              {'content-type' : 'application/xml; charset="utf-8"'})
        resp = urllib2.urlopen(req)
        resp_body = resp.read()
        namespaces = get_namespaces(StringIO.StringIO(resp_body))
        return fromstring(resp_body), namespaces

    def get_capabilities(self):
        (resp_root, namespaces) = self.call_ogc_api(tostring(self.build_get_capabitilies_request(),
                                                             'utf-8'))

        service = resp_root.find(get_cn_tag('ows:ServiceIdentification', namespaces))
        self.server = self.parse_service(service, namespaces)

        provider = resp_root.find(get_cn_tag('ows:ServiceProvider', namespaces))
        self.provider = self.parse_provider(provider, namespaces)

        operations = resp_root.find(get_cn_tag('ows:OperationsMetadata', namespaces))
        self.operations = self.parse_operations(operations, namespaces)

        filters = resp_root.find(get_cn_tag('sos:filterCapabilities', namespaces))
        #self.filters = self.parse_filters(filters, namespaces)

        offerings = resp_root.findall(get_cn_tag('sos:contents/sos:Contents/swes:offering',
                                                 namespaces))
        self.observations = []
        for offering in offerings:
            self.observations.append(self.parse_offering(offering, namespaces))


    def get_observation(self, offering, properties, time_range):
        req = self.build_get_observation_request(offering, properties, time_range)
        (resp_root, namespaces) = self.call_ogc_api(tostring(req, 'utf-8'))
        observations = resp_root.findall(get_cn_tag('sos:observationData/om:OM_Observation',
                                                    namespaces))
        measurements = {}
        for observation in observations:
            (dt, prop, value) = self.parse_observation(observation, namespaces)
            if dt not in measurements:
                measurements[dt] = {}
            measurements[dt][prop] = value

        return measurements

    def get_result(self, offering, properties, time_range):
        req = self.build_get_result_request(offering, properties, time_range)
        (resp_root, namespaces) = self.call_ogc_api(tostring(req, 'utf-8'))
        results = resp_root.find(get_cn_tag('sos:resultValues',
                                            namespaces)).text.strip().split('\n')

        measurements = {}
        prop_idx = 0
        prev_dt = None
        for l in results:
            elem = l.split(',')
            if len(elem) == 2:
                dt = datetime.strptime(elem[0], ISO8601_FMT)
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

    def update_capabilities(self):
        self.get_capabilities()


if __name__ == '__main__':
    pass
