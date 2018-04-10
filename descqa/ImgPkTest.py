from __future__ import unicode_literals, absolute_import, division
import os
import numpy as np
from .base import BaseValidationTest, TestResult
from .plotting import plt
from scipy import fftpack
import astropy.table

__all__ = ['ImgPkTest']

class ImgPkTest(BaseValidationTest):
    """
    Validation test that computes the power spectrum
    of a given raft image
    """
    def __init__(self,input_path,val_label,raft, **kwargs):
        self.input_path = input_path
        self.validation_data = astropy.table.Table.read(self.input_path)
        self.label = val_label
        self.raft = raft
    def post_process_plot(self, ax):
        ax.text(0.05, 0.95, self.input_path)
        ax.plot(self.validation_data['k'],self.validation_data['Pk'],
            label=self.label)
        ax.legend()

    def run_on_single_catalog(self, catalog_instance, catalog_name, output_dir):
        # The catalog instance is a focal plane
        test_raft = list(catalog_instance.focal_plane.rafts.values())[self.raft]
        if len(test_raft.sensors) != 9:
            return TestResult(skipped=True, summary='Raft is not complete')
        xdim, ydim = list(test_raft.sensors.values())[0].get_data().shape
        total_data = np.zeros((xdim*3,ydim*3))
        # Assemble the 3 x 3 raft's image: Need to use LSST's software to
        # handle the edges properly
        for i in range(0,3):
            for j in range(0,3):
                total_data[xdim*i:xdim*(i+1),ydim*j:ydim*(j+1)] = list(test_raft.sensors.values())[3*i+j].get_data()

        # FFT of the density contrast
        F1 = fftpack.fft2((total_data/np.mean(total_data)-1))
        F2 = fftpack.fftshift( F1 )
        psd2D = np.abs( F2 )**2 # 2D power
        pix_scale = 0.2/60*self.rebinning #pixel scale in arcmin
        kx = 1./pix_scale*np.arange(-F2.shape[0]/2,F2.shape[0]/2)*1./F2.shape[0]
        ky = 1./pix_scale*np.arange(-F2.shape[1]/2,F2.shape[1]/2)*1./F2.shape[1]
        kxx, kyy = np.meshgrid(kx,ky)
        rad = np.sqrt(kxx**2+kyy**2)
        bins = 1./pix_scale*np.arange(0,F2.shape[0]/2)*1./F2.shape[0]
        bin_space = bins[1]-bins[0]
        ps1d = np.zeros(len(bins))
        for i,b in enumerate(bins):
            ps1d[i] = np.mean(psd2D.T[(rad>b-0.5*bin_space) & (rad<b+0.5*bin_space)])/(F2.shape[0]*F2.shape[1])

        fig, ax = plt.subplots(2,1)
        for i in range(0,9):
            ax[0].hist(image[i].flatten(),histtype='step',label='Image: %d' % i)

        ax[1].plot(bins,ps1d,label=catalog_instace.sensor_raft)
        ax[1].set_xlabel('k [arcmin$^{-1}]')
        ax[1].set_ylabel('P(k)')
        self.post_process_plot(ax[1])
        fig.savefig(os.path.join(output_dir, 'plot.png'))
        # Check if the k binning/rebinning is the same before checking chi-sq
        if all(bins==self.validation_data['Pk']):
            score = (ps1d-self.validation_data['Pk'])
        # Check criteria to pass or fail (images in the edges of the focal plane
        # will have way more power than the ones in the center if they are not
        # flattened
        return TestResult(score, passed=True)

