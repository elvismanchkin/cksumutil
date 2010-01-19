#!/usr/bin/env python
import sys
import os
import re
import zlib, binascii, struct

if len(sys.argv) != 2:
    print 'Usage: ./crc_check.py path'
    sys.exit()
else:
    path = sys.argv[1]

def get_file_list():
    fl = sorted(os.listdir(path))
    filelist = []
    for d in fl:
        if os.path.isdir(os.path.join(path, d)) !=  True:
            # don't process directories recursively
            filelist.append(d)

    return filelist


# assumes that the crc is an 8 digit hex string
# in the filename between []
def extract_crc(filenamelist):
    crclist = []
    for filename in filenamelist:
        fentry = {}
        fentry['filename'] = filename
        fn = filename.upper()
        crcmatches = re.findall('\[([A-F0-9]{8})\]', fn)
        if len(crcmatches) == 1:
            fentry['crc_found'] = crcmatches[0]
        elif len(crcmatches) > 1:
            fentry['crc_found'] = 'error: more than 1 crc found in filename: ', crcmatches
        else:
            # len(crcmatches) == 0:
            fentry['crc_found'] = 'error: no crc found in filename'

        crclist.append(fentry)
    return crclist


def compute_crc(fentry):
    fn = fentry['filename']
    fo = file(os.path.join(path, fn), 'rb')
    bin = struct.pack('!l', zlib.crc32(fo.read()))
    computed_crc = binascii.hexlify(bin).upper()
    fentry['crc_computed'] = computed_crc

def check_crc(fentrylist):
    failed = []
    for fe in fentrylist:
        compute_crc(fe)
        if fe['crc_found'] == fe['crc_computed']:
            fe['result'] = 'OK'
        else:
            fe['result'] = 'CRC Error: found %s computed %s' % (fe['crc_found'], fe['crc_computed'])
            failed.append(fe)

        print '%s\t%s\t%s' % (fe['filename'], fe['crc_computed'], fe['result'])

    print '='*80
    print 'Summary:'
    print '%d files' % len(fentrylist)
    print '%d errors' % len(failed)
    if len(failed) > 0:
        print 'CRC Failed on:'
        for fe in failed:
            print fe

def main():
    print 'Scanning ', path
    filenames = get_file_list()
    crcs = extract_crc(filenames)
    check_crc(crcs)


main()


