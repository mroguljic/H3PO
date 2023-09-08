import awkward as ak
from coffea.nanoevents import NanoEventsFactory, NanoAODSchema
import numpy as np
import json


#---------------------------------------------
# Selection cuts
#---------------------------------------------
higgs_mass = 125.
delta_r_cut = 0.8
min_jet_mass = 50.

# FatJet cuts
ptcut = 250.
etacut = 2.5
mass_cut = [100.,150.]
pNet_cut = 0.9105

# Resolved jet cuts
res_ptcut = 30.
res_etacut = 2.5
res_mass_cut = [90.,150.]
# loose cut = 0.0532, med_cut = 0.3040, tight_cut = 0.7476 , https://twiki.cern.ch/twiki/bin/view/CMS/BtagRecommendation106XUL17   
res_deepBcut = 0.0532
#---------------------------------------------


def closest(masses):
    delta = abs(higgs_mass - masses)
    min_delta = ak.min(delta, axis=1)
    is_closest = (delta == min_delta)
    return is_closest


def HbbvsQCD(fatjet):
    score = (fatjet.particleNetMD_Xbb/(fatjet.particleNetMD_Xbb+fatjet.particleNetMD_QCD))
    return score

# this is a jet mask
def precut(fatjets):
    return (fatjets.pt>ptcut) & (np.absolute(fatjets.eta)<etacut)


def FailPassCategories(fatjets, jets=None):
    # sort the fat jets in the descending pNet HbbvsQCD score
    sorted_fatjets = fatjets[ak.argsort(-HbbvsQCD(fatjets),axis=-1)]

    # fail region: 0 fat jets passing the pNet cut
    # pass region: at least 1 fat jets passing the pNet cut
    fail_mask = (HbbvsQCD(sorted_fatjets[:,0])<=pNet_cut)
    pass_mask = (HbbvsQCD(sorted_fatjets[:,0])>pNet_cut)
    if jets is not None:
        return fatjets[fail_mask], fatjets[pass_mask], jets[fail_mask], jets[pass_mask]
    else:
        return fatjets[fail_mask], fatjets[pass_mask]

# this is a jet mask
def HiggsMassCut(fatjets):
    return (fatjets.msoftdrop>=mass_cut[0]) & (fatjets.msoftdrop<=mass_cut[1])

# this is a jet mask
def HiggsMassVeto(fatjets):
    return ((fatjets.msoftdrop<mass_cut[0]) | (fatjets.msoftdrop>mass_cut[1])) & (fatjets.msoftdrop>min_jet_mass)

# this is an event mask
def VR_b_JetMass_evtMask(fatjets):
    # jet mass window inverted for the 2 leading jets, applied to the 3rd one
    return (((fatjets[:,0].msoftdrop<mass_cut[0]) | (fatjets.msoftdrop[:,0]>mass_cut[1])) & (fatjets[:,0].msoftdrop>min_jet_mass) 
          & ((fatjets[:,1].msoftdrop<mass_cut[0]) | (fatjets[:,1].msoftdrop>mass_cut[1])) & (fatjets[:,1].msoftdrop>min_jet_mass)  
          & (fatjets[:,2].msoftdrop>=mass_cut[0]) & (fatjets[:,2].msoftdrop<=mass_cut[1]))


def Signal_boosted(fname,process,event_counts,eventsToRead=None):
    events = NanoEventsFactory.from_root(fname,schemaclass=NanoAODSchema,metadata={"dataset":process},entry_stop=eventsToRead).events()
    
    event_counts["Skim"] = len(events)
    
    fatjets = events.FatJet
    
    # fat jet preselection
    fatjets = fatjets[precut(fatjets)]
    
    # select events with at least 3 preselected fat jets
    fatjets = fatjets[ak.num(fatjets, axis=1)>2]
    
    event_counts["Preselection"] = len(fatjets)

    # apply the SR jet mass cut to preselected fat jets
    fatjets = fatjets[HiggsMassCut(fatjets)]

    # select events with at least 3 good fat jets. Pass on only the 3 leading fat jets (to avoid events passing or failing due to the 4th or higher leading fat jet)
    fatjets = fatjets[ak.num(fatjets, axis=1)>2][:,0:3]

    event_counts["Mass_cut"] = len(fatjets)

    return FailPassCategories(fatjets)


def Validation_boosted(fname,process,event_counts,eventsToRead=None):
    events = NanoEventsFactory.from_root(fname,schemaclass=NanoAODSchema,metadata={"dataset":process},entry_stop=eventsToRead).events()
    
    event_counts["Skim"] = len(events)
    
    fatjets = events.FatJet
    
    # fat jet preselection
    fatjets = fatjets[precut(fatjets)]
    
    # select events with at least 3 preselected fat jets
    fatjets = fatjets[ak.num(fatjets, axis=1)>2]
    
    event_counts["Preselection"] = len(fatjets)

    # for handling overlap with the SR
    fatjets_SR = fatjets
    fatjets_SR = fatjets_SR[HiggsMassCut(fatjets_SR)]
    # apply the VR jet mass cuts to the 3 leading (in pT) fat jets and reject overlap with the SR.
    # Pass on only the 3 leading fat jets (to avoid events passing or failing due to the pNet score of the 4th or higher leading fat jet)
    fatjets = fatjets[VR_b_JetMass_evtMask(fatjets) & ~(ak.num(fatjets_SR, axis=1)>2)][:,0:3]

    event_counts["Mass_cut"] = len(fatjets)

    return FailPassCategories(fatjets)


def Region_semiboosted(isSignal,fname,process,event_counts,eventsToRead=None):
    events = NanoEventsFactory.from_root(fname,schemaclass=NanoAODSchema,metadata={"dataset":process},entry_stop=eventsToRead).events()

    event_counts["Skim"] = len(events)

    fatjets = events.FatJet

    # fat jet preselection
    fatjets = fatjets[precut(fatjets)]
    
    # select events with at least 3 preselected fat jets
    events_preselection =  events[ak.num(fatjets, axis=1)>2]
    fatjets             = fatjets[ak.num(fatjets, axis=1)>2]

    event_counts["Preselection_fatjets"] = len(fatjets)
    
    # for handling overlap with the boosted selection
    fatjets_SR_boosted = fatjets
    if not isSignal:
        fatjets_SR_boosted = fatjets_SR_boosted[HiggsMassCut(fatjets_SR_boosted)]
    fatjets_VR_boosted = fatjets
    # apply the jet mass cut to preselected fat jets
    if isSignal:
        fatjets = fatjets[HiggsMassCut(fatjets)]
    else:
        fatjets = fatjets[:,0:2]
        fatjets = fatjets[HiggsMassVeto(fatjets)]

    # select events with exactly 2 good fat jets and reject overlap with the SR and the boosted selection
    if isSignal:
        events_semiboosted_fatjets = events_preselection[(ak.num(fatjets, axis=1)==2) & ~(VR_b_JetMass_evtMask(fatjets_VR_boosted))]
        fatjets                    =             fatjets[(ak.num(fatjets, axis=1)==2) & ~(VR_b_JetMass_evtMask(fatjets_VR_boosted))]
    else:
        events_semiboosted_fatjets = events_preselection[(ak.num(fatjets, axis=1)==2) & ~(VR_b_JetMass_evtMask(fatjets_VR_boosted) | (ak.num(fatjets_SR_boosted, axis=1)>=2))]
        fatjets                    =             fatjets[(ak.num(fatjets, axis=1)==2) & ~(VR_b_JetMass_evtMask(fatjets_VR_boosted) | (ak.num(fatjets_SR_boosted, axis=1)>=2))]

    event_counts["Mass_cut_fatjets"] = len(fatjets)

    # get resolved jets from selected events
    jets = events_semiboosted_fatjets.Jet

    # apply preselection to the resolved jets
    jets = jets[(jets.pt > res_ptcut) & (np.absolute(jets.eta) < res_etacut) & (jets.btagDeepB>res_deepBcut)]

    # require that there are at least 2 good jets present in the event
    fatjets = fatjets[ak.num(jets, axis=1)>1]
    jets    =    jets[ak.num(jets, axis=1)>1]

    event_counts["Preselection_jets"] = len(jets)

    # require jets to be away from fat jets
    away_jets_mask = jets.nearest(fatjets).delta_r(jets)>delta_r_cut
    jets = jets[away_jets_mask]

    # require that there are at least 2 good away jets present in the event
    fatjets = fatjets[ak.num(jets, axis=1)>1]
    jets    =    jets[ak.num(jets, axis=1)>1]

    event_counts["Away_jets"] = len(jets)

    # calculate mass of all possible jet pairs and select the pair which has the mass closest to the Higgs boson mass
    dijets = ak.combinations(jets, 2, fields=['i0', 'i1'])
    dijet_masses = (dijets['i0'] + dijets['i1']).mass
    is_closest = closest(dijet_masses)
    closest_dijets = dijets[is_closest]
    # apply the jet mass cut to the closest dijets
    good_dijets = closest_dijets[((closest_dijets['i0'] + closest_dijets['i1']).mass>=res_mass_cut[0]) & ((closest_dijets['i0'] + closest_dijets['i1']).mass<=res_mass_cut[1])]
    
    # select events with at least 1 good dijet (by construction there can be at most 1 per event)
    fatjets     =     fatjets[ak.num(good_dijets, axis=1)>0]
    good_dijets = good_dijets[ak.num(good_dijets, axis=1)>0]

    event_counts["Good_dijet"] = len(good_dijets)

    return FailPassCategories(fatjets, good_dijets)


def Signal_semiboosted(fname,process,event_counts,eventsToRead=None):
    return Region_semiboosted(True,fname,process,event_counts,eventsToRead=None)


def Validation_semiboosted(fname,process,event_counts,eventsToRead=None):
    return Region_semiboosted(False,fname,process,event_counts,eventsToRead=None)


def Region_semiboosted_eq2(mask,fname,process,event_counts,eventsToRead=None):
    events = NanoEventsFactory.from_root(fname,schemaclass=NanoAODSchema,metadata={"dataset":process},entry_stop=eventsToRead).events()

    event_counts["Skim"] = len(events)

    fatjets = events.FatJet

    # fat jet preselection
    fatjets = fatjets[precut(fatjets)]
    
    # select events with exactly 2 preselected fat jets (by construction orthogonal to the boosted selection)
    events_preselection =  events[ak.num(fatjets, axis=1)==2]
    fatjets             = fatjets[ak.num(fatjets, axis=1)==2]

    event_counts["Preselection_fatjets"] = len(fatjets)
    
    # apply the jet mass cut to preselected fat jets
    fatjets = fatjets[mask(fatjets)]

    # select events with exactly 2 good fat jets
    events_semiboosted_fatjets = events_preselection[ak.num(fatjets, axis=1)==2]
    fatjets                    =             fatjets[ak.num(fatjets, axis=1)==2]

    event_counts["Mass_cut_fatjets"] = len(fatjets)
    
    # get resolved jets from selected events
    jets = events_semiboosted_fatjets.Jet

    # apply preselection to the resolved jets
    jets = jets[(jets.pt > res_ptcut) & (np.absolute(jets.eta) < res_etacut) & (jets.btagDeepB>res_deepBcut)]

    # require that there are at least 2 good jets present in the event
    fatjets = fatjets[ak.num(jets, axis=1)>1]
    jets    =    jets[ak.num(jets, axis=1)>1]

    event_counts["Preselection_jets"] = len(jets)

    # require jets to be away from fat jets
    away_jets_mask = jets.nearest(fatjets).delta_r(jets)>delta_r_cut
    jets = jets[away_jets_mask]

    # require that there are at least 2 good away jets present in the event
    fatjets = fatjets[ak.num(jets, axis=1)>1]
    jets    =    jets[ak.num(jets, axis=1)>1]

    event_counts["Away_jets"] = len(jets)

    # calculate mass of all possible jet pairs and select the pair which has the mass closest to the Higgs boson mass
    dijets = ak.combinations(jets, 2, fields=['i0', 'i1'])
    dijet_masses = (dijets['i0'] + dijets['i1']).mass
    is_closest = closest(dijet_masses)
    closest_dijets = dijets[is_closest]
    # apply the jet mass cut to the closest dijets
    good_dijets = closest_dijets[((closest_dijets['i0'] + closest_dijets['i1']).mass>=res_mass_cut[0]) & ((closest_dijets['i0'] + closest_dijets['i1']).mass<=res_mass_cut[1])]
    
    # select events with at least 1 good dijet (by construction there can be at most 1 per event)
    fatjets     =     fatjets[ak.num(good_dijets, axis=1)>0]
    good_dijets = good_dijets[ak.num(good_dijets, axis=1)>0]

    event_counts["Good_dijet"] = len(good_dijets)

    return FailPassCategories(fatjets, good_dijets)


def Signal_semiboosted_eq2(fname,process,event_counts,eventsToRead=None):
    return Region_semiboosted_eq2(HiggsMassCut,fname,process,event_counts,eventsToRead=None)


def Validation_semiboosted_eq2(fname,process,event_counts,eventsToRead=None):
    return Region_semiboosted_eq2(HiggsMassVeto,fname,process,event_counts,eventsToRead=None)
