import os
def read_json_file(abspth_to_fl=None,pth=None, flnm=None):
    '''
    read json file from full_path
    TODO: remove print statements (?)
    '''
    if not abspth_to_fl:
        abspth_to_fl = os.path.join(pth,flnm)
    if not os.path.exists(abspth_to_fl):
        print('Invalid filename (readingfile.read_json_file): ', abspth_to_fl)
        file = None

    else:
        try:
            with open(abspth_to_fl, 'r') as f:
                file = json.load(f)

        except Exception as e:
            print('Error in json-file: ', e)
            raise Exception(f'Could not read jsonfile: {abspth_to_fl}')

            file = None
    return file