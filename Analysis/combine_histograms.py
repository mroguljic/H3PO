from os import listdir, getcwd, system, chdir
from os.path import isfile, join
from argparse import ArgumentParser
from condor.datasets import *
import ROOT
import json
import re 
import copy


def get_dataset_scaling_factor(process,year,sumGen):
    json_file = open(H3_DIR + "/xsecs.json")
    config = json.load(json_file)
    xsec    = config[year][process]["xsec"]
    luminosity  = config[year]["lumi"]
    scaling     = (xsec*luminosity)/sumGen
    return scaling


def get_number_of_events_in_dataset(list_of_root_files):
    nev = 0
    for root_fname in list_of_root_files:
        froot = ROOT.TFile.Open(root_fname, 'READ')
        nevHisto = froot.Get("numberOfGenEventsHisto")
        nev += nevHisto.GetBinContent(1)
        froot.Close()
    return nev


def normalize_histograms(identifier, year, deleteFiles=False, startsWithRegion=True):
    regions = ["Histograms"]
    
    for region in regions:
        list_of_root_files = []
        cwd = getcwd()
        list_of_root_files = get_list_of_root_files(cwd, identifier, region, startsWithRegion)
        nev_in_sample = get_number_of_events_in_dataset(list_of_root_files)
        scale = get_dataset_scaling_factor(identifier, year, nev_in_sample)
        for root_fname in list_of_root_files:
            if not deleteFiles:
                system("cp -p {0} unscaled_{1}".format(root_fname,root_fname))
            froot = ROOT.TFile.Open(root_fname, 'UPDATE')
            list_of_keys = copy.deepcopy(froot.GetListOfKeys()) # without deepcopy the processing time explodes, no idea why
            for myKey in list_of_keys:
                if re.match ('TH', myKey.GetClassName()):
                    hname = myKey.GetName()
                    if (hname == "numberOfGenEventsHisto"):
                        continue                    
                    h = froot.Get(hname)
                    h.Scale(scale)
                    h.Write("", ROOT.TObject.kOverwrite)
            froot.Close()


def get_list_of_root_files(cwd, identifier, region, startsWithRegion):
    list_of_root_files = []
    for file in listdir(cwd):
        if not isfile(join(cwd, file)):
            continue
        if (file.startswith(identifier) if not startsWithRegion else ('_'+identifier+'-') in file) and file.endswith('.root') and (file.startswith(region) if startsWithRegion else ('_'+region) in file):
            list_of_root_files.append(file)
    return list_of_root_files


def remove_root_files(list_of_root_files):
    for file in list_of_root_files:
        system('rm ' + file)


def mv_file(dir, file):
    system("mkdir -p {0}".format(dir))
    system("mv {0} {1}".format(file,dir))

def combine_histograms(identifier, deleteFiles=False, skipNorm=False, startsWithRegion=True, mvFiles=False, fit_dir="fit"):
    
    regions = ["Histograms"]
    
    for region in regions:
        list_of_root_files = []
        cwd = getcwd()

        list_of_root_files = get_list_of_root_files(cwd, identifier, region, startsWithRegion)
        filename = "{0}_{1}.root".format(identifier,region)

        # in case of only one source file, make sure that the source and target files do not have identical names. Otherwise, hadding is not needed
        if (len(list_of_root_files)==1 and filename==list_of_root_files[0]):
            if mvFiles:
                mv_file(fit_dir, filename)
        else:
            system("hadd -f {0} {1}".format(filename," ".join(list_of_root_files)))
            if deleteFiles:
                remove_root_files(list_of_root_files)
            else:
                if startsWithRegion and not skipNorm:
                    for root_fname in list_of_root_files:
                        system("mv unscaled_{0} {1}".format(root_fname,root_fname))
            if mvFiles:
                mv_file(fit_dir, filename)


if __name__ == '__main__':
    # usage example
    Description = "Example: %(prog)s -i condor_jobs_<timestamp>"
    
    # input parameters
    parser = ArgumentParser(description=Description)

    parser.add_argument("-i", "--input", dest="input",
                      help="Input directory name",
                      metavar="INPUT",
                      required=True)
    
    parser.add_argument("-f", "--fit_dir", dest="fit_dir",
                      help="Fit directory name (default: %(default)s)",
                      default="fit",
                      metavar="FIT_DIR")

    parser.add_argument("-y", "--year", dest="year",
                        help="Data taking year (default: %(default)s)",
                        default="2017",
                        metavar="YEAR")
    
    parser.add_argument("-p", "--processes", dest="processes",
                        help="Space-separated list of processes (default: %(default)s)",
                        nargs='*',
                        default=["QCD","TTbar","JetHT","XToYHTo6B_MX-2400_MY-800"],
                        metavar="PROCESSES")
    
    parser.add_argument("--delete_files", dest="delete_files", action='store_true',
                      help="Delete Condor output root files (default: %(default)s)",
                      default=False)
    
    parser.add_argument("--skip_norm", dest="skip_norm", action='store_true',
                        help="Specify if histograms should be normalized (default: %(default)s)",
                        default=False)


    (options, args) = parser.parse_known_args()
    
    chdir(options.input)
    
    if not options.skip_norm:
        print ("Performing normalization...")
        for dataset in datasets[options.year]:
            if not dataset.startswith(tuple(options.processes)):
                continue
            if ("JetHT" in dataset):
                print ("Skipping {0} during normalization".format(dataset))
                continue
            print ("Processing {0}".format(dataset))
            normalize_histograms(dataset, options.year, options.delete_files)
        print ("Normalization done")

    print ("Merging dataset files...")
    for dataset in datasets[options.year]:
        if not dataset.startswith(tuple(options.processes)):
            continue
        print ("Processing {0}".format(dataset))
        combine_histograms(dataset, options.delete_files, options.skip_norm)
    print ("Merging dataset files done")

    print ("Merging process files...")
    for process in options.processes:
        print ("Processing {0}".format(process))
        combine_histograms(process, True, options.skip_norm, False, True, options.fit_dir)
    print ("Merging process files done")
