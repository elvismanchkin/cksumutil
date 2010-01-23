#!/usr/bin/env python
import sys, os, re
import zlib, binascii, struct
import hashlib
import optparse

def check_dir(option, opt_str, value, parser):
    path = value
    print 'Scanning ', path
    print
    filenames = get_file_list(path)
    crcs = extract_crc(filenames)
    check_crc(path, crcs)
    return

def check_md5file(option, opt_str, value, parser):
    md5fn = value
    print 'Processing ', value
    print
    md5s = extract_md5(md5fn)
    path = os.path.split(value)[0]
    check_md5(path, md5s)
    return

def check_sfvfile(option, opt_str, value, parser):
    return

def get_file_list(path):
    fl = sorted(os.listdir(path))
    filelist = []
    for d in fl:
        if os.path.isdir(os.path.join(path, d)) !=  True:
            # don't process directories recursively
            filelist.append(d)

    return filelist

def extract_md5(md5fn):
    md5list = []
    md5fo = open(md5fn)
    line = md5fo.readline()
    while line:
        md5entry = {}
        md5sum = re.findall('([A-F0-9]{32})', line.upper())
        md5sum = md5sum[0]
        md5starti = line.upper().index(md5sum)
        md5endi = md5starti + len(md5sum)
        # each line in an md5 file has the following format:
        # 32 character md5 sum
        # one ' ' character
        # if the file is a text file: one ' ' character
        # else if the file is a binary file: one '*' character
        # the filename
        filename = line[md5endi+2:]
        md5entry['md5_found'] = md5sum
        md5entry['filename'] = filename.strip()
        md5list.append(md5entry)

        line = md5fo.readline()

    md5fo.close()
    return md5list

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

def compute_md5(path, fentry):
    fn = fentry['filename']
    try:
        fo = file(os.path.join(path, fn), 'rb')
        fentry['md5_computed'] = hashlib.md5(fo.read()).hexdigest().upper()
    except IOError as (errno, strerror):
        fentry['md5_computed'] = 'IO Error %d: %s' % (errno, strerror)

    return

def check_md5(path, md5list):
    failed = []
    for fe in md5list:
        compute_md5(path, fe)
        if fe['md5_found'] == fe['md5_computed']:
            fe['result'] = 'OK'
        else:
            fe['result'] = 'MD5 Error: found %s computed %s' % (fe['md5_found'], fe['md5_computed'])
            failed.append(fe)

        print '%s\t%s' % (fe['result'], fe['filename'])

    print '='*80
    print 'Summary:'
    print '%d files' % len(md5list)
    print '%d errors' % len(failed)
    if len(failed) > 0:
        print 'MD5 Failed on:'
        for fe in failed:
            print '%s result: %s' % (fe['filename'], fe['result'])

    return

def compute_crc(path, fentry):
    fn = fentry['filename']
    fo = file(os.path.join(path, fn), 'rb')
    bin = struct.pack('!l', zlib.crc32(fo.read()))
    computed_crc = binascii.hexlify(bin).upper()
    fentry['crc_computed'] = computed_crc

def check_crc(path, fentrylist):
    failed = []
    for fe in fentrylist:
        compute_crc(path, fe)
        if fe['crc_found'] == fe['crc_computed']:
            fe['result'] = 'OK'
        else:
            fe['result'] = 'CRC Error: found %s computed %s' % (fe['crc_found'], fe['crc_computed'])
            failed.append(fe)

        print '%s\t%s' % (fe['result'], fe['filename'])

    print '='*80
    print 'Summary:'
    print '%d files' % len(fentrylist)
    print '%d errors' % len(failed)
    if len(failed) > 0:
        print 'CRC Failed on:'
        for fe in failed:
            print '%s result: %s' % (fe['filename'], fe['result'])

def main():
    parser = optparse.OptionParser()
    parser.add_option('-d', '--dir',
                      action="callback", callback=check_dir,
                      type="string",
                      help="""directory with filenames of the form: foo[crc32].ext\
                           The file's crc32 checksum will be computed and\
                           compared against the one in their filename.
                           """)
    parser.add_option('-m', '--md5',
                      action="callback", callback=check_md5file,
                      type="string",
                      help=".md5 file to check")
    parser.add_option('-s', '--sfv',
                      action="callback", callback=check_sfvfile,
                      type="string",
                      help=".sfv file to check")
    parser.parse_args()
    return


main()


