## Summary

Command line utility for interacting with trustar data


## Install 

Simplest way to install is using pip:

```
$ pip3 install bnpdtrustar
```

## Configure

Obtain your APIKEY and SECRETKEY from Trustar and make a config file.  By default, the script will look for a file named _trustar.conf_ in cwd.  You may override this behavior with --config option.

Config file format is dictated by trustar and, at the time of this writing it looks like this:

```
############################################################
# Template  python SDK configuration file
[trustar]

# Endpoints
auth_endpoint = https://api.trustar.co/oauth/token
api_endpoint = https://api.trustar.co/api/1.3-beta

# Config
user_api_key = YOUR API KEY HERE 
user_api_secret = YOUR API SECRET HERE 
```

## Usage

Execute bpndtrustar with --help option for details.

