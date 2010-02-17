#!/usr/bin/env python
import sys, os, re
import zlib, binascii, struct
import hashlib
import optparse

FILENAME = 'filename'
CHECKSUM_FOUND = 'checksum_found'
CHECKSUM_COMPUTED = 'checksum_computed'
RESULT = 'result'
ERROR_MSG = 'error_msg'
MD5 = 'md5'
CRC = 'crc32'

def create_sfvfile(option, opt_str, value, parser):
    sfvfn = value
    filelist = []
    for fn in parser.rargs: # globbing is already done!
        fentry = {}
        fentry[FILENAME] = fn
        compute_crc('./', fentry)
        filelist.append(fentry)

    try:
        fo = open(sfvfn, 'w')
        for fe in filelist:
            fo.write('%s %s\r\n' %( fe[FILENAME], fe[CHECKSUM_COMPUTED]))
        fo.flush()
        fo.close()
        
    except IOError as (errno, strerror):
        print 'IO Error %d: %s' % (errno, strerror)
        return

    return

def check_dir(option, opt_str, value, parser):
    path = value
    filenames = get_file_list(path)
    crcs = extract_crc(filenames)
    check_files(CRC, path, crcs)
    return

def check_md5file(option, opt_str, value, parser):
    md5fn = value
    md5s = extract_md5(md5fn)
    path = os.path.split(value)[0]
    check_files(MD5, path, md5s)
    return

def check_sfvfile(option, opt_str, value, parser):
    sfvfn = value
    sfvs = extract_sfv(sfvfn)
    path = os.path.split(value)[0]
    check_files(CRC, path, sfvs)
    return

def get_file_list(path):
    fl = sorted(os.listdir(path))
    filelist = []
    for d in fl:
        if os.path.isdir(os.path.join(path, d)) !=  True:
            # don't process directories recursively
            filelist.append(d)

    return filelist

def extract_sfv(sfvfn):
    sfvlist = []
    sfvfo = open(sfvfn)
    line = sfvfo.readline()
    while line:
        if line[0] != ';': # sfv comment
            sfventry = {}
            sfvln = line.split(' ')
            sfventry[FILENAME] = sfvln[0]
            sfventry[CHECKSUM_FOUND] = sfvln[1].strip().upper()
            sfvlist.append(sfventry)

        line = sfvfo.readline()

    sfvfo.close()
    return sfvlist

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
        md5entry[CHECKSUM_FOUND] = md5sum
        md5entry[FILENAME] = filename.strip()
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
        fentry[FILENAME] = filename
        fn = filename.upper()
        crcmatches = re.findall('\[([A-F0-9]{8})\]', fn)
        if len(crcmatches) == 1:
            fentry[CHECKSUM_FOUND] = crcmatches[0]
        elif len(crcmatches) > 1:
            fentry[ERROR_MSG] = 'More than 1 CRC found in filename.'
        else:
            fentry[ERROR_MSG] = 'No CRC found in filename.'

        crclist.append(fentry)
    return crclist

def compute_md5(path, fentry):
    fn = fentry[FILENAME]
    try:
        fo = file(os.path.join(path, fn), 'rb')
        fentry[CHECKSUM_COMPUTED] = hashlib.md5(fo.read()).hexdigest().upper()
    except IOError as (errno, strerror):
        fentry[ERROR_MSG] = 'IO Error %d: %s' % (errno, strerror)
    return

def compute_crc(path, fentry):
    fn = fentry[FILENAME]
    try:
        fo = file(os.path.join(path, fn), 'rb')
        bin = struct.pack('!l', zlib.crc32(fo.read()))
        computed_crc = binascii.hexlify(bin).upper()
        fentry[CHECKSUM_COMPUTED] = computed_crc
    except IOError as (errno, strerror):
        fentry[ERROR_MSG] = 'IO Error %d: %s' % (errno, strerror)
    return

def check_files(type, path, filelist):
    failed = []
    for fe in filelist:
        # check if there was a file error
        if fe.has_key(ERROR_MSG):
            fe[RESULT] = 'Error'
            failed.append(fe)
        else:
            # no error, go compute checksum
            if type == MD5:
                compute_md5(path, fe)
            elif type == CRC:
                compute_crc(path, fe)

            if fe[CHECKSUM_FOUND] == fe[CHECKSUM_COMPUTED]:
                fe[RESULT] = 'OK'
            else:
                fe[RESULT] = 'Error'
                fe[ERROR_MSG] = 'Found %s but computed %s.'\
                    % (fe[CHECKSUM_FOUND], fe[CHECKSUM_COMPUTED])
                failed.append(fe)

        print '%s\t%s' % (fe[RESULT], fe[FILENAME])

    print_summary(filelist, failed)
    return    

def print_summary(filelist, failedlist):
    print '='*80
    print 'Summary:'
    print '%d files' % len(filelist)
    print '%d errors' % len(failedlist)
    if len(failedlist) > 0:
        print
        print 'Checksum failed on:'
        for fe in failedlist:
                print '%s\t%s' % (fe[FILENAME], fe[ERROR_MSG])

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
    parser.add_option('--create-sfv',
                      action="callback", callback=create_sfvfile,
                      type="string",
                      help="""The first argument is the desired sfv file name.\
                           The second argument is a Unix path expression\
                           e.g., file*.txt OR a list of files.\
                           Subdirectories will not be traversed.
                           """)

    if len(sys.argv) == 1:
        parser.print_help()

    print
    (options, args) = parser.parse_args()
    return

if __name__ == '__main__':
    main()
