# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
fectch anatomical files/resmapleing surfaces to fsl32k 
^^^^^^^^^^^^^^^^^^^^^^^^
.. autofunction:: init_structral_wf

"""

import os,fnmatch,shutil
from pathlib import Path
from templateflow.api import get as get_template
from ..utils import collect_data,CiftiSurfaceResample
from nipype.interfaces.freesurfer import MRIsConvert
from ..interfaces.connectivity import ApplyTransformsx
from niworkflows.engine.workflows import LiterateWorkflow as Workflow
from pkg_resources import resource_filename as pkgrf
from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype import MapNode as MapNode
from ..interfaces import BrainPlotx, RibbontoStatmap
from ..utils import bid_derivative

class DerivativesDataSink(bid_derivative):
     out_path_base = 'xcp_d'

def init_anatomical_wf(
     omp_nthreads,
     fmri_dir,
     subject_id,
     output_dir,
     t1w_to_mni,
     input_type,
     mem_gb,
     name='anatomical_wf',
      ):
     """
     This workflow is convert surfaces (gifti) from fMRI to standard space-fslr-32k
     It also resmaple t1w t1w segmnetation to standard space, MNI

     Workflow Graph
          .. workflow::
               :graph2use: orig
               :simple_form: yes
               from xcp_d.workflows import init_anatomical_wf
               wf = init_anatomical_wf(
                omp_nthreads,
                fmri_dir,
                subject_id,
                output_dir,
                t1w_to_mni,
                name="anatomical_wf",
                )
     Parameters
     ----------
     omp_nthreads : int
          number of threads
     fmri_dir : str
          fmri output directory
     subject_id : str
          subject id
     output_dir : str
          output directory
     t1w_to_mni : str
          t1w to MNI transform
     name : str
          workflow name

     Inputs
     ------
     t1w: str
          t1w file
     t1w_seg: str
          t1w segmentation file
    
     """
     workflow = Workflow(name=name)

     inputnode = pe.Node(niu.IdentityInterface(
        fields=['t1w','t1seg']),
        name='inputnode')

     

     
     MNI92FSL  = pkgrf('xcp_d', 'data/transform/FSL2MNI9Composite.h5')
     mnitemplate = str(get_template(template='MNI152NLin6Asym',resolution=2, suffix='T1w')[-1])
     layout,subj_data = collect_data(bids_dir=fmri_dir,participant_label=subject_id,bids_validate=False)

     if input_type == 'dcan' or input_type == 'hcp':
          ds_t1wmni_wf = pe.Node(
               DerivativesDataSink(base_directory=output_dir, space='MNI152NLin6Asym',desc='preproc',suffix='T1w',
                  extension='.nii.gz'),
                  name='ds_t1wmni_wf', run_without_submitting=False)
     
          ds_t1wseg_wf = pe.Node(
           DerivativesDataSink(base_directory=output_dir, space='MNI152NLin6Asym',suffix='dseg',
              extension='.nii.gz'),
                  name='ds_t1wseg_wf', run_without_submitting=False)
          workflow.connect([
          (inputnode,ds_t1wmni_wf,[('t1w','in_file')]),
          (inputnode,ds_t1wseg_wf,[('t1seg','in_file')]),
          (inputnode,ds_t1wmni_wf,[('t1w','source_file')]),
          (inputnode,ds_t1wseg_wf,[('t1w','source_file')]),
          ])
         
          all_files  = list(layout.get_files())
          L_inflated_surf  = fnmatch.filter(all_files,'*sub-*'+ subject_id + '*hemi-L_inflated.surf.gii')[0]
          R_inflated_surf  = fnmatch.filter(all_files,'*sub-*'+ subject_id +'*hemi-R_inflated.surf.gii')[0]
          L_midthick_surf  = fnmatch.filter(all_files,'*sub-*'+ subject_id +'*hemi-L_midthickness.surf.gii')[0]
          R_midthick_surf  = fnmatch.filter(all_files,'*sub-*'+ subject_id +'*hemi-R_midthickness.surf.gii')[0]
          L_pial_surf  = fnmatch.filter(all_files,'*sub-*'+ subject_id +'*hemi-L_pial.surf.gii')[0]
          R_pial_surf  = fnmatch.filter(all_files,'*sub-*'+ subject_id +'*hemi-R_pial.surf.gii')[0]
          L_wm_surf  = fnmatch.filter(all_files,'*sub-*'+ subject_id +'*hemi-L_smoothwm.surf.gii')[0]
          R_wm_surf  = fnmatch.filter(all_files,'*sub-*'+ subject_id +'*hemi-R_smoothwm.surf.gii')[0]
     
          ribbon = fnmatch.filter(all_files,'*sub-*'+ subject_id + '*desc-ribbon.nii.gz')[0]

          ses_id =_getsesid(ribbon) 
          anatdir = output_dir+'/xcp_d/sub-'+ subject_id +'/ses-'+ ses_id+ '/anat'
          if not os.path.exists(anatdir):
               os.makedirs(anatdir)

          surf = [L_inflated_surf,R_inflated_surf,L_midthick_surf,R_midthick_surf,L_pial_surf,
               R_pial_surf,L_wm_surf,R_wm_surf]
          
          for ss in surf:
               shutil.copy(ss,anatdir)
    
          ribbon2statmap_wf = pe.Node(RibbontoStatmap(ribbon=ribbon),name='ribbon2statmap',mem_gb=mem_gb,n_procs=omp_nthreads)
         
          brainspritex_wf = pe.Node(BrainPlotx(),name='brainsprite',mem_gb=mem_gb,n_procs=omp_nthreads)
          
          ds_brainspriteplot_wf = pe.Node(
            DerivativesDataSink(base_directory=output_dir,check_hdr=False,dismiss_entities=['desc'], desc='brainplot', datatype="figures"),
                  name='brainspriteplot', run_without_submitting=True)

          workflow.connect([
              
               (ribbon2statmap_wf,brainspritex_wf,[('out_file','in_file')]),
                (inputnode,brainspritex_wf,[('t1w','template')]),
               (brainspritex_wf,ds_brainspriteplot_wf,[('out_html','in_file')]),
               (inputnode,ds_brainspriteplot_wf,[('t1w','source_file')]),
          ])
          
     else:

          t1w_transform_wf = pe.Node(ApplyTransformsx(num_threads=2,reference_image=mnitemplate,
                       transforms=[str(t1w_to_mni),str(MNI92FSL)],interpolation='LanczosWindowedSinc',
                       input_image_type=3, dimension=3),
                       name="t1w_transform", mem_gb=mem_gb,n_procs=omp_nthreads)

          seg_transform_wf = pe.Node(ApplyTransformsx(num_threads=2,reference_image=mnitemplate,
                       transforms=[str(t1w_to_mni),str(MNI92FSL)],interpolation="MultiLabel",
                       input_image_type=3, dimension=3),
                       name="seg_transform",mem_gb=mem_gb,n_procs=omp_nthreads)

          ds_t1wmni_wf = pe.Node(
           DerivativesDataSink(base_directory=output_dir, space='MNI152NLin6Asym',desc='preproc',suffix='T1w',
                  extension='.nii.gz'),
                  name='ds_t1wmni_wf', run_without_submitting=False)
     
          ds_t1wseg_wf = pe.Node(
           DerivativesDataSink(base_directory=output_dir, space='MNI152NLin6Asym',suffix='dseg',
           extension='.nii.gz'),
                  name='ds_t1wseg_wf', run_without_submitting=False)

          workflow.connect([
           (inputnode,t1w_transform_wf, [('t1w', 'input_image')]),
           (inputnode,seg_transform_wf, [('t1seg', 'input_image')]),
           (t1w_transform_wf,ds_t1wmni_wf,[('output_image','in_file')]),
           (seg_transform_wf,ds_t1wseg_wf,[('output_image','in_file')]),
           (inputnode,ds_t1wmni_wf,[('t1w','source_file')]),
           (inputnode,ds_t1wseg_wf,[('t1w','source_file')]),
            ])

     #verify fresurfer directory
     
          p = Path(fmri_dir)
          import glob as glob
          freesufer_paths = glob.glob(str(p.parent)+'/freesurfer*') # for fmriprep and nibabies
          if len(freesufer_paths)  == 0 :
               freesufer_paths = glob.glob(str(p)+'/sourcedata/*freesurfer*') # nibabies

          if len(freesufer_paths) > 0 and 'freesurfer' in os.path.basename(freesufer_paths[0]):
               freesufer_path = freesufer_paths[0]
          else:
               freesufer_path = None
    
          if  freesufer_path != None and os.path.isdir(freesufer_path):

               all_files  = list(layout.get_files())
               L_inflated_surf  = fnmatch.filter(all_files,'*sub-*'+ subject_id + '*hemi-L_inflated.surf.gii')[0]
               R_inflated_surf  = fnmatch.filter(all_files,'*sub-*'+ subject_id +'*hemi-R_inflated.surf.gii')[0]
               L_midthick_surf  = fnmatch.filter(all_files,'*sub-*'+ subject_id +'*hemi-L_midthickness.surf.gii')[0]
               R_midthick_surf  = fnmatch.filter(all_files,'*sub-*'+ subject_id +'*hemi-R_midthickness.surf.gii')[0]
               L_pial_surf  = fnmatch.filter(all_files,'*sub-*'+ subject_id +'*hemi-L_pial.surf.gii')[0]
               R_pial_surf  = fnmatch.filter(all_files,'*sub-*'+ subject_id +'*hemi-R_pial.surf.gii')[0]
               L_wm_surf  = fnmatch.filter(all_files,'*sub-*'+ subject_id +'*hemi-L_smoothwm.surf.gii')[0]
               R_wm_surf  = fnmatch.filter(all_files,'*sub-*'+ subject_id +'*hemi-R_smoothwm.surf.gii')[0]

          # get sphere surfaces to be converted
               if 'sub-' not in subject_id:
                    subid ='sub-'+ subject_id
               else:
                    subid = subject_id
          
               left_sphere = str(freesufer_path)+'/'+subid+'/surf/lh.sphere.reg'
               right_sphere = str(freesufer_path)+'/'+subid+'/surf/rh.sphere.reg'  
          
               left_sphere_fsLR = str(get_template(template='fsLR',hemi='L',density='32k',suffix='sphere')[0])
               right_sphere_fsLR = str(get_template(template='fsLR',hemi='R',density='32k',suffix='sphere')[0]) 

          # nodes for letf and right in node
               left_sphere_mris_wf = pe.Node(MRIsConvert(out_datatype='gii',in_file=left_sphere),name='left_sphere',mem_gb=mem_gb,n_procs=omp_nthreads)
               right_sphere_mris_wf = pe.Node(MRIsConvert(out_datatype='gii',in_file=right_sphere),name='right_sphere',mem_gb=mem_gb,n_procs=omp_nthreads)
          
         
          ## surface resample to fsl32k
               left_wm_surf_wf = pe.Node(CiftiSurfaceResample(new_sphere=left_sphere_fsLR, 
                        metric = ' BARYCENTRIC ',in_file=L_wm_surf), name="left_wm_surf",mem_gb=mem_gb,n_procs=omp_nthreads)
               left_pial_surf_wf = pe.Node(CiftiSurfaceResample(new_sphere=left_sphere_fsLR, 
                        metric = ' BARYCENTRIC ',in_file=L_pial_surf), name="left_pial_surf",mem_gb=mem_gb,n_procs=omp_nthreads)
               left_midthick_surf_wf = pe.Node(CiftiSurfaceResample(new_sphere=left_sphere_fsLR, 
                        metric = ' BARYCENTRIC ',in_file=L_midthick_surf), name="left_midthick_surf",mem_gb=mem_gb,n_procs=omp_nthreads)
               left_inf_surf_wf = pe.Node(CiftiSurfaceResample(new_sphere=left_sphere_fsLR, 
                        metric = ' BARYCENTRIC ',in_file=L_inflated_surf), name="left_inflated_surf",mem_gb=mem_gb,n_procs=omp_nthreads)
          

               right_wm_surf_wf = pe.Node(CiftiSurfaceResample(new_sphere=right_sphere_fsLR, 
                        metric = ' BARYCENTRIC ',in_file=R_wm_surf), name="right_wm_surf",mem_gb=mem_gb,n_procs=omp_nthreads)
               right_pial_surf_wf = pe.Node(CiftiSurfaceResample(new_sphere=right_sphere_fsLR, 
                        metric = ' BARYCENTRIC ',in_file=R_pial_surf), name="right_pial_surf",mem_gb=mem_gb,n_procs=omp_nthreads)
               right_midthick_surf_wf = pe.Node(CiftiSurfaceResample(new_sphere=right_sphere_fsLR, 
                        metric = ' BARYCENTRIC ',in_file=R_midthick_surf), name="right_midthick_surf",mem_gb=mem_gb,n_procs=omp_nthreads)
               right_inf_surf_wf = pe.Node(CiftiSurfaceResample(new_sphere=right_sphere_fsLR, 
                        metric = ' BARYCENTRIC ',in_file=R_inflated_surf), name="right_inflated_surf",mem_gb=mem_gb,n_procs=omp_nthreads)

          
          # write report node
               ds_wmLsurf_wf = pe.Node(
                  DerivativesDataSink(base_directory=output_dir, dismiss_entities=['desc'], density='32k',desc='smoothwm',check_hdr=False,
                 extension='.surf.gii',hemi='L',source_file=L_wm_surf), name='ds_wmLsurf_wf', run_without_submitting=False,mem_gb=2)
          
               ds_wmRsurf_wf = pe.Node(
                  DerivativesDataSink(base_directory=output_dir, dismiss_entities=['desc'], density='32k',desc='smoothwm',check_hdr=False,
                  extension='.surf.gii',hemi='R',source_file=R_wm_surf), name='ds_wmRsur_wf', run_without_submitting=False,mem_gb=2)
          
               ds_pialLsurf_wf = pe.Node(
                 DerivativesDataSink(base_directory=output_dir,dismiss_entities=['desc'], density='32k',desc='pial',check_hdr=False,
                extension='.surf.gii',hemi='L',source_file=L_pial_surf), name='ds_pialLsurf_wf', run_without_submitting=True,mem_gb=2)
               ds_pialRsurf_wf = pe.Node(
                 DerivativesDataSink(base_directory=output_dir,dismiss_entities=['desc'], density='32k',desc='pial',check_hdr=False,
                 extension='.surf.gii',hemi='R',source_file=R_pial_surf), name='ds_pialRsurf_wf', run_without_submitting=False,mem_gb=2)

               ds_infLsurf_wf = pe.Node(
                 DerivativesDataSink(base_directory=output_dir,dismiss_entities=['desc'],density='32k',desc='inflated',check_hdr=False,
                 extension='.surf.gii',hemi='L',source_file=L_inflated_surf), name='ds_infLsurf_wf', run_without_submitting=False,mem_gb=2)

               ds_infRsurf_wf = pe.Node(
                 DerivativesDataSink(base_directory=output_dir,dismiss_entities=['desc'], density='32k',desc='inflated',check_hdr=False,
                 extension='.surf.gii',hemi='R',source_file=R_inflated_surf), name='ds_infRsurf_wf', run_without_submitting=False,mem_gb=2)

               ds_midLsurf_wf = pe.Node(
                 DerivativesDataSink(base_directory=output_dir,dismiss_entities=['desc'], density='32k',desc='midthickness',check_hdr=False,
                extension='.surf.gii',hemi='L',source_file=L_midthick_surf), name='ds_midLsurf_wf', run_without_submitting=False,mem_gb=2)

               ds_midRsurf_wf = pe.Node(
                  DerivativesDataSink(base_directory=output_dir,dismiss_entities=['desc'],density='32k',desc='midthickness',check_hdr=False,
                  extension='.surf.gii',hemi='R',source_file=R_midthick_surf), name='ds_midRsurf_wf', run_without_submitting=False,mem_gb=2)

          

               workflow.connect([ 
                (left_sphere_mris_wf,left_wm_surf_wf,[('converted','current_sphere')]),
                (left_sphere_mris_wf,left_pial_surf_wf,[('converted','current_sphere')]),
                (left_sphere_mris_wf,left_midthick_surf_wf,[('converted','current_sphere')]),
                (left_sphere_mris_wf,left_inf_surf_wf,[('converted','current_sphere')]),

                (right_sphere_mris_wf,right_wm_surf_wf,[('converted','current_sphere')]),
                (right_sphere_mris_wf,right_pial_surf_wf,[('converted','current_sphere')]),
                (right_sphere_mris_wf,right_midthick_surf_wf,[('converted','current_sphere')]),
                (right_sphere_mris_wf,right_inf_surf_wf,[('converted','current_sphere')]),

                (left_wm_surf_wf,ds_wmLsurf_wf,[('out_file','in_file')]),
                (left_pial_surf_wf,ds_pialLsurf_wf,[('out_file','in_file')]),
                (left_midthick_surf_wf,ds_midLsurf_wf,[('out_file','in_file')]),
                (left_inf_surf_wf,ds_infLsurf_wf,[('out_file','in_file')]),

                (right_wm_surf_wf,ds_wmRsurf_wf,[('out_file','in_file')]),
                (right_pial_surf_wf,ds_pialRsurf_wf,[('out_file','in_file')]),
                (right_midthick_surf_wf,ds_midRsurf_wf,[('out_file','in_file')]),
                (right_inf_surf_wf,ds_infRsurf_wf,[('out_file','in_file')]),
                ]) 

               t1w_mgz  = str(freesufer_path) + '/'+subid+'/mri/orig.mgz'
               ribbon = str(freesufer_path) + '/'+subid+'/mri/ribbon.mgz'

      
          
               ribbon2statmap_wf = pe.Node(RibbontoStatmap(ribbon=ribbon),name='ribbon2statmap',mem_gb=mem_gb,n_procs=omp_nthreads)
     
          
          #brainplot
               brainspritex_wf = pe.Node(BrainPlotx(template=t1w_mgz),name='brainsprite',mem_gb=mem_gb,n_procs=omp_nthreads)
          
               ds_brainspriteplot_wf = pe.Node(
               DerivativesDataSink(base_directory=output_dir,check_hdr=False,dismiss_entities=['desc'], desc='brainplot', datatype="figures"),
                  name='brainspriteplot')

               workflow.connect([
               #(pial2vol_wf,addwmpial_wf,[('out_file','in_file')]),
               #(wm2vol_wf,addwmpial_wf,[('out_file','operand_files')]),
                (ribbon2statmap_wf,brainspritex_wf,[('out_file','in_file')]),
     
                (brainspritex_wf,ds_brainspriteplot_wf,[('out_html','in_file')]),
                (inputnode,ds_brainspriteplot_wf,[('t1w','source_file')]),
               ])
     
          else:
               ribbon2statmap_wf = pe.Node(RibbontoStatmap(),name='ribbon2statmap',mem_gb=mem_gb,n_procs=omp_nthreads)
               brainspritex_wf = pe.Node(BrainPlotx(),name='brainsprite',mem_gb=mem_gb,n_procs=omp_nthreads)
               ds_brainspriteplot_wf = pe.Node(
                 DerivativesDataSink(base_directory=output_dir,check_hdr=False, dismiss_entities=['desc',], desc='brainplot', datatype="figures"),
                  name='brainspriteplot')

               workflow.connect([
                (inputnode,brainspritex_wf,[('t1w','template')]),
                (inputnode,ribbon2statmap_wf,[('t1seg','ribbon')]),
                (ribbon2statmap_wf,brainspritex_wf,[('out_file','in_file')]),
                (brainspritex_wf,ds_brainspriteplot_wf,[('out_html','in_file')]),
                (inputnode,ds_brainspriteplot_wf,[('t1w','source_file')]),
                 ])
     
     return workflow

 


def _getsesid(filename):
     ses_id = None
     filex = os.path.basename(filename)

     file_id = filex.split('_')
     for k in file_id:
          if 'ses' in k: 
               ses_id = k.split('-')[1]
               break 

     return ses_id
