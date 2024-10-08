# Koala: Key frame-conditioned long video-LLM
<!-- **Koala: Key frame-conditioned long video-LLM** -->

This is the repository for our Koala model, which introduces a video-LLM for understanding minutes-long videos and answering questions about them. 

<!--<div style='display:flex; gap: 0.25rem; '>
<a href='https://modelscope.cn/studios/damo/video-llama/summary'><img src='https://img.shields.io/badge/ModelScope-Demo-blueviolet'></a>
<a href='https://www.modelscope.cn/models/damo/videollama_7b_llama2_finetuned/summary'><img src='https://img.shields.io/badge/ModelScope-Checkpoint-blueviolet'></a>
<a href='https://huggingface.co/spaces/DAMO-NLP-SG/Video-LLaMA'><img src='https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Demo-blue'></a>
<a href='https://huggingface.co/DAMO-NLP-SG/Video-LLaMA-2-7B-Finetuned'><img src='https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Checkpoint-blue'></a> 
<a href='https://arxiv.org/abs/2306.02858'><img src='https://img.shields.io/badge/Paper-PDF-red'></a>
</div>-->

## Introduction
Koala is built on top of [BLIP-2](https://github.com/salesforce/LAVIS/tree/main/projects/blip2) and [MiniGPT-4](https://github.com/Vision-CAIR/MiniGPT-4). 

## Pre-trained & Fine-tuned Checkpoints

The following checkpoints store learnable parameters (positional embedding layers, Video/Audio Q-former, and linear projection layers) only. To download our evaluation weights, please do so from this [link](https://drive.google.com/file/d/1rGI095o-p_wQP4p1jOzy9hUV_PHCgY4_/view?usp=drive_link). Please note that this may only be a temporary link due to an upcoming limit on google drive storage. I will update this link once I have found a more permanent storage location. 


## Usage
#### Enviroment Preparation 

First, install ffmpeg.
```
apt update
apt install ffmpeg
```
Then, create a conda environment:
```
conda env create -f environment.yml
conda activate koala-model
```


## Prerequisites

Before using the repository, make sure you have obtained the following checkpoints:

#### Pre-trained Language Decoder

- Get the original LLaMA weights in the Hugging Face format by following the instructions [here](https://huggingface.co/docs/transformers/main/model_doc/llama).
- Download Vicuna delta weights :point_right: [[7B](https://huggingface.co/lmsys/vicuna-7b-delta-v0)][[13B](https://huggingface.co/lmsys/vicuna-13b-delta-v0)] (Note: we use **v0 weights** instead of v1.1 weights). 
- Use the following command to add delta weights to the original LLaMA weights to obtain the Vicuna weights:

```
python apply_delta.py \
    --base /path/to/llama-13b \
    --target /output/path/to/vicuna-13b --delta /path/to/vicuna-13b-delta
```

#### Pre-trained Visual Encoder in Vision-Language Branch
- Download the MiniGPT-4 model (trained linear layer) from this [link](https://drive.google.com/file/d/1a4zLvaiDBr-36pasffmgpvH5P7CKmpze/view).

## Training

We train our Koala model on instructional videos from a subset of HowTo100m dataset. Please follow the preprocessing steps mentioned before to extract video frames for training.

### 1. Finetuning
#### Data Preparation
Download the metadata and videos using the instructions from the official webpage of [HowTo100m](https://www.di.ens.fr/willow/research/howto100m/). Then, you can extract the video frames by running the script:
```
python -W ignore preprocessing_scripts/extract_video_frames.py --video_dir {path to directory where downloaded videos are stored} --output_dir {path to directory for storing extracted frames}
```

Please note that this script automatically deletes each video once the video frames have been extracted from it to save storage memory. Additionally, once all the frames have been extracted, please create a pickle file from a list containing the valid video frames named **all_videos.pkl** and store in a data directory.

Finally, the downloaded HowTo100M dataset should also contain an annotation file named **HowTo100M_v1.csv**. Please process it to create a dictionary that maps video ids to their corresponding task labels which can be found in the file **task_ids.csv**. Save this dictionary as **vid2label.pkl** and store it in the same data directory as all_videos.pkl.

#### Script
Config the the checkpoint and dataset paths in [video_aggregation_finetune.yaml](./koala/train_configs/video_aggregation_finetune.yaml).
Run the script:
```
conda activate koala-model
python -W ignore train.py --cfg-path ./koala/train_configs/video_aggregation_finetune.yaml --num_gpus {number of GPUs} --num_workers {worker threads} --batch_size {total batch size over number of GPUs}
```

### 2. Evaluation
#### EgoSchema Data Preparation
Please begin by downloading the annotation files and videos from the official webpage of [EgoSchema](https://github.com/egoschema/EgoSchema). Then, you can extract the video frames by running the same script as mentioned above.

#### Evaluation Script
Once the evaluation data has been preprocessed, start the evaluation process by running the following command:
```
python -W ignore eval_qa_egoschema.py --caption_output_dir {path to directory for storing the model predictions} --video_dir {path to directory that contains the extracted frames} --data_dir {path to directory that contains EgoSchema annotation files}
```

## Launch Demo on Local Machine
Set the `llama_model` (this is the path to the pretrained weights of the language model) in [koala/eval_configs/conversation_demo.yaml](./koala/eval_configs/conversation_demo.yaml) accordingly. 
Then, you can launch the demo with the model on a local machine by running the script:
```
python demo_video.py \
    --cfg-path eval_configs/conversation_demo.yaml \
    --model_type llama_v2
    --pretrained_weight_path {path to pretrained weights}
```

### To-do
- [ x ] Clean evaluation scripts
- [ ] Refactor evaluation code component for ease of understanding

## Acknowledgements
We would like to acknowledge the following approaches that allow us to build our work upon:
* [LAVIS](https://github.com/salesforce/LAVIS): LAVIS - A Library for Language-Vision Intelligence
* [MiniGPT-4](https://github.com/Vision-CAIR/MiniGPT-4): Enhancing Vision-language Understanding with Advanced Large Language Models
* [BLIP-2](https://github.com/salesforce/LAVIS/tree/main/projects/blip2): Bootstrapping Language-Image Pre-training with Frozen Image Encoders and Large Language Models 
* [EVA-CLIP](https://github.com/baaivision/EVA/tree/master/EVA-CLIP): Improved Training Techniques for CLIP at Scale
* [LLaMA](https://github.com/facebookresearch/llama): Open and Efficient Foundation Language Models
* [VideoChat](https://github.com/OpenGVLab/Ask-Anything): Chat-Centric Video Understanding
* [LLaVA](https://github.com/haotian-liu/LLaVA): Large Language and Vision Assistant
* [Video-LLaMA](https://github.com/DAMO-NLP-SG/Video-LLaMA): Video-LLaMA: An Instruction-tuned Audio-Visual Language Model for Video Understanding


<!--The logo of Video-LLaMA is generated by [Midjourney](https://www.midjourney.com/). -->


## Terms of Use
Our Koala video-LLM model is a research endeavor intended for non-commercial use only. Please do not use our model for any possible nefarious purposes.

## Citation
If you find our project useful, please consider citing our paper as well as the abovementioned approaches:
```
@article{TanKoala2024,
  author = {Reuben Tan and Ximeng Sun and Ping Hu and Jui-hsien Wang and Hanieh Deilamsalehy and Bryan A. Plummer and Bryan Russell and Kate Saenko},
  title = {Koala: Key frame-conditioned long video-LLM},
  year = 2024,
  booktitle={The IEEE Conference on Computer Vision and Pattern Recognition (CVPR)},
}
```

## Contact
Please do not hesitate to contact me at rxtan@bu.edu if you have any questions.

