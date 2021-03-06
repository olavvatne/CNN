import sys, os
import numpy as np
#Makes sh scripts find modules.
sys.path.append(os.path.abspath("./"))

from interface.command import get_command
from printing import print_section, print_action
from storage import ParamStorage
from config import filename_params, dataset_params, dataset_path
from dataset_create import CurriculumDataset

'''
This tool pre-generate a patch dataset. The tool is especially necessary for curriculum learning. The reason for not
doing this every time the network is trained, is that a previously trained model needs to be loaded in order to do
difficulty estimation. There are several properties that can be set, when using command line.
-baseline: No difficulty estimation
-stages: Array with floats, setting difficulty threshold per stage. Please refrain from using space inside array.
-tradeoff: Previously trained curriculum teacher's best precision and recall tradeoff. (threshold value)
-dataset: Path to dataset. IE
-initsamples: Samples per image for first stage
-currsamples: Samples per image for remaining stages
-teacher: Curriculum teacher model
-save: Path to where pre-generated patch dataset should be stored.

REMEMBER: The patch creator is initialized using the config.py file.
'''
print_section("TOOLS: Creating curriculum learning dataset")

# Baseline will create a curriculum with no example ordering, but same amount of examples.
# Avoids results from curriculum learning to be caused by the model just having seen more examples.
is_baseline, baseline = get_command('-baseline')

is_stages, stages = get_command('-stages', default="[0.1, 1.0]")
stages = np.array(eval(stages))

#Precision recall breakeven point. 0.5 used as a default.
is_tradeoff, tradeoff = get_command('-tradeoff')
if is_tradeoff:
    tradeoff = float(tradeoff)

#Dataset path. Config used if not supplied
is_alt_dataset, alt_dataset = get_command('-dataset')
if is_alt_dataset:
    dataset_path = alt_dataset

#Initial stage sample size
is_init_size, init_stage_sample = get_command('-initsamples', default=dataset_params.samples_per_image)
init_stage_sample = int(init_stage_sample)

# Stage 1 - N sample size
is_curr_size, curr_stage_sample = get_command('-currsamples', default=str(init_stage_sample))
curr_stage_sample = int(curr_stage_sample)

#Teacher params location. Config used if not supplied
is_teacher_location, teacher_location = get_command('-teacher')
if not is_teacher_location:
    teacher_location = filename_params.curriculum_teacher

#Curriculum dataset save path. Config used if not supplied.
is_save_path, save_path = get_command('-save')
if not is_save_path:
    save_path = filename_params.curriculum_location

#Load the curriculum teacher which provide consistency estimates for extracted examples.
store = ParamStorage()
teacher = store.load_params(path=teacher_location)

generator = CurriculumDataset(teacher, dataset_path, save_path, dataset_params, tradeoff)
generator.create_dataset(is_baseline, thresholds=stages, base_sample=init_stage_sample,
                         secondary_sample=curr_stage_sample)