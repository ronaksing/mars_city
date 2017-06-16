from __future__ import division, print_function

import os
import sys
import ConfigParser

import numpy as np
import pandas as pd

from atrial_fibrillation import AtrialFibrillation
from ventricular_tachycardia import VentricularTachycardia


class AnomalyDetector(object):
    """
    implements methods to call various Anomaly Detection Algorithms
    """

    def __init__(self):
        self.config = ConfigParser.RawConfigParser()
        dirname = os.path.dirname(os.path.abspath(sys.argv[0]))
        cfg_filename = os.path.join(dirname, 'anomaly_detector.cfg')
        self.config.read(cfg_filename)

    def af_anomaly_detect(self, rr_intervals, hr_quality_indices):
        """
        executes the Atrial Fibrillation Anomaly detection
        Input:
            rr_intervals:           a 2D pandas dataframe -
                                    (refer rrinterval.txt from Hexoskin record)
                                    first column named "hexoskin_timestamps" -
                                    contains 'int' timestamps
                                    second column named as "rr_int" -
                                    contains 'double' interval data
            hr_quality_indices:     a 2D pandas dataframe -
                                    (refer hr_quality.txt from Hexoskin record)
                                    first column named "hexoskin_timestamps" -
                                    containts 'int' timestamps
                                    second column named as "quality_ind" -
                                    contains 'int' quality indices,
                                    with max value 127

        Output:
            returns:
            if anomaly:
                'dict' with follwing keys:
                    start_hexo_timestamp:   an integer denoting timestamp of
                                            the first record
                    end_hexo_timestamp:     an integer denoting timestamp of
                                            32/64/128 - last record
                    num_of_NEC:             a small integer, higher the number,
                                            more severe the anomaly here
                    data_reliability:       a small integer, which denotes as a
                                            percentage, the quality of the data
                                            in this window
                                            the higher the percentage, worse
                                            the quality
                    window_size:            a small integer, takes 32/64/128
                                            as values
            else:
                None
        Notes:
            based on 'A Simple Method to Detect
            Atrial Fibrillation Using RR Intervals'
            by Jie Lian et. al.
            Note the return value (if not 'None') and
            check with the data_reliability and previous
            data timestamps to set AFAlarmAttribute at
            the health_monitor server
        """
        AF = AtrialFibrillation(rr_intervals, hr_quality_indices,
                                self.config)
        return AF.get_anomaly()

    def vt_anomaly_detect(self, ecg, rr_intervals, rr_interval_status, prev_ampl):
        """
         __zero_one_count - if it is the string 'True', it means that analysis of next 6 seconds is required
                          - if it is None, it means that next 6 second analysis is not required
                          - if it has an integer value then it means that a VT event has been detected and it
                            has to be stored in the anomaly database
        """
        __zero_one_count = 'True'
        VTobj = VentricularTachycardia(ecg, rr_intervals, rr_interval_status, self.config)
        further_analyze = VTobj.analyze_six_second()
        if not further_analyze:
            __zero_one_count = None
            return VTobj.mean_ampl, __zero_one_count
        
        print("Doing further analysis")
        VTobj.signal_preprocess()
        cur_ampl, stop_cur = VTobj.DHA_detect(prev_ampl)
        
        # whatever be the results of the following stages, we have to analyze the next six second epoch
        if stop_cur == True:
            return VTobj.mean_ampl, __zero_one_count

        # asystole detector
        vtvfres = VTobj.asystole_detector(cur_ampl)

        # to analyze next six second epoch
        if vtvfres == 'VT/VF':
            print(vtvfres)
            __zero_one_count = VTobj.zero_one_count
            return VTobj.mean_ampl, __zero_one_count
        else:
            print(vtvfres)
            return VTobj.mean_ampl, __zero_one_count

def main():
    AD = AnomalyDetector()
    rr_intervals = (pd.read_csv('rrinterval.txt',
                    sep="\t",
                    nrows=AD.config.getint('Atrial Fibrillation',
                                           'window_size'),
                    dtype={"hexoskin_timestamps": np.int64,
                           "rr_int": np.float64},
                    header=None,
                    names=["hexoskin_timestamps", "rr_int"]))
    hr_quality_indices = (pd.read_csv('hr_quality.txt',
                                      sep="\t",
                                      nrows=AD.config.
                                      getint('Atrial Fibrillation',
                                             'window_size')-8,
                                      dtype={"hexoskin_timestamps": np.int64,
                                             "quality_ind": np.int32},
                                      header=None,
                                      names=["hexoskin_timestamps",
                                             "quality_ind"]))
    # call the Atrial Fibrillation anomaly detection method
    # print(AD.af_anomaly_detect(rr_intervals, hr_quality_indices))

    ecg = (pd.read_csv('ecg.txt',
                    sep="\t",
                    nrows=256*6,
                    dtype={"hexoskin_timestamps": np.int64,
                           "ecg_val": np.int32},
                    header=None,
                    names=["hexoskin_timestamps", "ecg_val"]))
    # for testing, ensure that only the relevant timestamped rr_intervals are present in rrinterval.txt
    rr_intervals = (pd.read_csv('rrinterval.txt',
                    sep="\t",
                    nrows=7,
                    dtype={"hexoskin_timestamps": np.int64,
                           "rr_int": np.float64},
                    header=None,
                    names=["hexoskin_timestamps", "rr_int"]))
    # for testing, ensure that only the relevant timestamped rr_status are present in rr_interval_status.txt
    rr_interval_status = (pd.read_csv('rr_interval_status.txt',
                          sep="\t",
                          nrows=7,
                          dtype={"hexoskin_timestamps": np.int64,
                                 "rr_status": np.int32},
                          header=None,
                          names=["hexoskin_timestamps", "rr_status"]))
    # call the Ventricular Tachycardia anomaly detection method
    AD.vt_anomaly_detect(ecg, rr_intervals, rr_interval_status, 1400)

if __name__ == '__main__':
    main()
