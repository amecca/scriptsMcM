#!/usr/bin/env python

################################################################################
#  Script that tries to find the path to the gridpack from the DAS dataset name
#  Copyright (C) 2023  Alberto Mecca (alberto.mecca@cern.ch)
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
################################################################################

from __future__ import print_function
import sys
import re
import logging
from argparse import ArgumentParser
sys.path.append('/afs/cern.ch/cms/PPD/PdmV/tools/McM/')
from rest import McM

def parse_args():
    parser = ArgumentParser(description='Script that tries to find the path to the gridpack from the full DAS dataset name')
    parser.add_argument('dataset')
    parser.add_argument('-c', '--campaign', help='Select a particular LHEGEN campaign')
    parser.add_argument('-v', '--verbose', action='count'      , dest='verbosity', default=1, help='Increase verbosity')
    parser.add_argument('-q', '--quiet'  , action='store_const', dest='verbosity', const=0  , help='Set verbosity to 0')
    parser.add_argument(      '--debug'  , action='store_true', help='Switch McM debug logging')
    parser.add_argument(      '--dump'   , action='store_true', help='Dump the fragment of the GEN step to a file')
    parser.add_argument('--log', dest='loglevel', metavar='LEVEL', default='WARNING', help='Level for the python logging module. Can be either a mnemonic string like DEBUG, INFO or WARNING or an integer (lower means more verbose).')
    return parser.parse_args()

def select_campaign(campaigns, dataset_split=[], args_campaign=None, verbosity=0):
    '''
    Select the correct campaign if possible
    '''
    # A specific campaign was requested
    if(args_campaign is not None):
        campaigns = [ c for c in campaigns if args_campaign in c['prepid'] ]
        if(verbosity > 0):
            logging.info("filtered campaigns %d: %s\n", len(campaigns), [ c['prepid'] for c in campaigns ])

    # Use the dataset name to deduce the campaign
    if(len(dataset_split) > 1):
        match = re.search("Run(IX|IV|V?I{0,3}|\d)[^\d]+20(UL)*\d{2}", dataset_split[1])  # matches up to Run9 / RunIX
        if match is not None:
            campaigns = [ c for c in campaigns if match.group() in c['prepid'] ]
            if(verbosity > 0):
                logging.info("filtered campaigns %d: %s\n", len(campaigns), [ c['prepid'] for c in campaigns ])

    theCampaign = sorted(campaigns, key=lambda c: c['prepid'], reverse=True)[0]

    return theCampaign

def dump_fragment(campaign, fname):
    with open(fname, "w") as f:
        f.write(campaign['fragment'])

def main():
    args = parse_args()
    loglevel = args.loglevel.upper() if not args.loglevel.isdigit() else int(args.loglevel)
    logging.basicConfig(format='%(levelname)s:%(module)s:%(funcName)s: %(message)s', level=loglevel)

    dataset_split = args.dataset.strip('/').split('/')
    dataset = dataset_split[0]
    logging.info('Requested dataset: "%s"', dataset)

    mcm = McM(dev=False, debug=args.debug)
    campaign_requests = mcm.get('requests', query='dataset_name={:s}'.format(dataset))

    if(not len(campaign_requests) >= 1):
        logging.error('No campaigns found for dataset "{:s}"'.format(dataset))
        return 1

    genCampaigns = [c for c in campaign_requests if "LHE" in c['prepid']]
    if(not len(genCampaigns) >= 1):
        logging.error('No LHE campaigns found for dataset "{:s}"'.format(dataset))
        return 1

    logging.info("LHE campaigns found: %s", len(genCampaigns))
    if(args.verbosity > 1):
        for prepid in [c['prepid'] for c in genCampaigns]:
            logging.info("\t"+prepid)

    # Select the campaign using the information we have
    theCampaign = select_campaign(genCampaigns, dataset_split=dataset_split, args_campaign=args.campaign)
    logging.info("Chosen campaign: %s", theCampaign['prepid'])

    # Open the fragment and search the line that contains the tarball location
    lines = theCampaign['fragment'].split('\n')
    if(len(lines) == 0):
        logging.error('ERROR: Unable to get fragment for campaign "%s"', theCampaign['prepid'])
        return 1

    lines.sort(
        key=lambda line: (                      # tuples are sorted by their first element, then the second, etc.
            'args' in line,                     # we're looking for the args of the ExternalLHEProducer
            '/cvmfs' in line,                   # the path must be in cvmfs
            'tar.gz' in line or 'tgs' in line,  # looking for a tarball
        ), reverse=True )


    dump_fname = theCampaign['prepid']+"_fragment.dump"

    match = re.search("/cvmfs/[^'\"]+", lines[0])
    if match is not None:
        print(match.group())
    else:
        dump_fragment(theCampaign, dump_fname)
        logging.error('Could find tarball name in fragment. Content written to "%s"', dump_fname)
        return 2

    if(args.dump):
        dump_fragment(theCampaign, dump_fname)
        logging.info('fragment dumped to "%s"', dump_fname)

    return 0

if __name__ == '__main__':
    exit(main())
