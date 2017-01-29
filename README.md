# sosclient
OGC SOS API module and its sample (simple shell interface)

## ogcsosapi




## ogcsos_shell

ogcsos_shell is a simple shell interface for SOS API.
You can use it just for using SOS API or sample python script to use SOS API from your code.

There is two way to use this script, shell mode and command mode as bellow:

### shell mode

To use shell mode of it, run ogcsos_shell.py with --token option.
At first the script executes GetCapabilities, so it takes a while.
After that you will see SOS shell prompt 'SOS: ' and you can execute some commands.

```shell-sesstion
$ ./ogcsos_shell.py --token xxxxxxxxxxx
Simple Shell Interface for OGC SOS API by Satoru MIYAMOTO

Welcome to SOS Server !

SOS: 
```

#### server command
shows the server information.

```shell-session
SOS: server
SOS Server: 
 service type     : OGC:SOS
 service version  : 2.0.0
 service fees     : NONE
 served operations:
       GetCapabilities,DescribeSensor,GetObservation,GetResultTemplate,GetResult
```

#### provider command
shows provider of the server information.

```shell-session
SOS: provider
xxxx University: 
 administrator  xxxxx: 
 address:
     xxxxxxxxx
```

#### nodes command
shows sensor nodes (observation offerings) list in the server.

```shell-session
SOS: nodes
 1: FieldRouter-001
 2: Shinshu-NGYU
 3: WeatherStation-LUFFT
...
```
with -l option, it shows a list with detailed description.

```shell-session
SOS: nodes -l
 1: FieldRouter-001 : vbox0151  FR Id of X-Ability
 2: Shinshu-NGYU : Shinshu Camera
 3: WeatherStation-LUFFT : Lufft Weather Station
...
```

#### sensors command
shows sensors (observed properties) list in specified sensor node.
To specify a sensor node, you can use a number in sensor nodes list given by 'nodes' command or a name of the sensor node.

```shell-session
SOS: sensors 3
 1: air_temperature
 2: relative_humidity
 3: air_pressure
 4: wind_speed
 5: 10min_maximum_wind_speed
 6: 10min_minimum_wind_speed
 7: 10min_average_wind_speed
 8: wind_direction
 9: 1min_precipitation
10: solar_irradiance
11: 10min_maximum_solar_irradiance
12: 10min_minimum_solar_irradiance
13: 10min_average_solar_irradiance

SOS: sensors WeatherStation-LUFFT
 1: air_temperature
 2: relative_humidity
 3: air_pressure
 4: wind_speed
 5: 10min_maximum_wind_speed
 6: 10min_minimum_wind_speed
 7: 10min_average_wind_speed
 8: wind_direction
 9: 1min_precipitation
10: solar_irradiance
11: 10min_maximum_solar_irradiance
12: 10min_minimum_solar_irradiance
13: 10min_average_solar_irradiance
```

#### measures command
get measurements of specified sensors of a node and time range.
To specify a sensor node, you can use a number or a name of it with -n option.
To specify sensors, you can use a number in sensors list given by 'sensors' command or a name of the sensor. You can specify multiple sensors with separator space.
In Following example, 1st and 2nd sensor(air_temperature, relative_humidity) in 3rd sensor node (WeatherStation-LUFFT) is specified.

```shell-session
SOS: measures -n 3 1 2
time,air_temperature,relative_humidity
2017-01-29 11:28:00,11.5,39.9
2017-01-29 11:29:00,11.6,39.7
2017-01-29 11:30:00,11.7,40.8
2017-01-29 11:31:00,11.8,40.7
2017-01-29 11:32:00,11.9,39.9
```

Also you can do it as below:

```shell-session
SOS: measures -n WeatherStation-LUFFT air_temperature relative_humidity
time,air_temperature,relative_humidity
2017-01-29 11:28:00,11.5,39.9
2017-01-29 11:29:00,11.6,39.7
2017-01-29 11:30:00,11.7,40.8
2017-01-29 11:31:00,11.8,40.7
2017-01-29 11:32:00,11.9,39.9
```

Without time range option, it gets measurements in past 5 minutes.
You can specify time range using -s and -e option.

```shell-session
SOS: measures -n 3 -s 2017-01-20T00:00:00 -e 2017-01-20T00:03:00 1 2
time,air_temperature,relative_humidity
2017-01-20 00:00:00,2.2,66.3
2017-01-20 00:01:00,2.2,66.5
2017-01-20 00:02:00,2.1,66.6
2017-01-20 00:03:00,2.1,66.8
```

A variety of time formats is allowed as bellow:

* %Y%m%d%H%M
* %Y-%m-%dT%H:%M:%S
* %Y-%m-%dT%H:%M
* %Y-%m-%d
* %H:%M:%S
* %H:%M
* %H%M

If time is not specified, it is interpreted time is 00:00:00.

```shell-session
SOS: measures -n 3 -s 2017-01-20 -e 2017-01-21 1 2
time,air_temperature,relative_humidity
2017-01-20 00:00:00,2.2,66.3
2017-01-20 00:01:00,2.2,66.5
2017-01-20 00:02:00,2.1,66.6
2017-01-20 00:03:00,2.1,66.8
2017-01-20 00:04:00,2.1,66.9
...
2017-01-20 23:57:00,3.5,78.6
2017-01-20 23:58:00,3.4,79.1
2017-01-20 23:59:00,3.3,79.6
2017-01-21 00:00:00,3.3,80.0
```

If date is not specified, it is interpreted date is today.

```shell-session
SOS: measures -n 3 -s 0800 -e 0805 1 2
time,air_temperature,relative_humidity
2017-01-29 08:00:00,2.4,73.2
2017-01-29 08:01:00,2.4,72.0
2017-01-29 08:02:00,2.6,71.9
2017-01-29 08:03:00,2.7,71.1
2017-01-29 08:04:00,2.7,71.0
2017-01-29 08:05:00,2.9,70.5
```

### command mode

You can use command mode of this script to run from your own scripts.
To do so, run it with --token and --command option.
You can specify a command same as one you can use in shell mode.

```shell-session
$ ./ogcsos_shell.py --token xxxx --command 'measures -n 3 1 2'
time,air_temperature,relative_humidity
2017-01-29 11:45:00,11.7,39.1
2017-01-29 11:46:00,11.8,39.9
2017-01-29 11:47:00,12.0,39.2
2017-01-29 11:48:00,11.9,39.0
2017-01-29 11:49:00,11.8,39.6
2017-01-29 11:50:00,11.8,40.3
```

You can still use a number of sensor node or sensor in the command, but it takes a while because it has to execute GetCapabilities.
You may want to get results faster by specifying exact name of sensor node or sensor.
You can use --instant option to do it. In this case, you have to specify an exact name of sensor node, eg. 'TEST:Field:SenserNodeName'.

```shell-session
$ ./ogcsos_shell.py --token xxxx --command 'measures -n TEST:Field:WeatherStation-LUFFT air_temperature relative_humidity' --instant
time,air_temperature,relative_humidity
2017-01-29 12:41:00,13.2,29.8
2017-01-29 12:42:00,13.1,31.1
2017-01-29 12:43:00,13.2,31.6
2017-01-29 12:44:00,13.5,30.4
2017-01-29 12:45:00,13.3,30.1
2017-01-29 12:46:00,13.2,31.2
```

This software is released under the MIT License, see LICENSE.txt.

