from configparser import ConfigParser

def ConfigSectionMap(section):
    dict1 = {}
    config = ConfigParser()
    config.read("deployment/environment.cfg")

    for key in config[section]:
        try:
            dict1[key] = config.get(section, key)
            if dict1[key] == -1:
                DebugPrint("skip: %s" % key)
        except:
            print("exception on %s!" % key)
            dict1[key] = None
    return dict1