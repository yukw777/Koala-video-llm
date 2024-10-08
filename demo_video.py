"""
Adapted from: https://github.com/Vision-CAIR/MiniGPT-4/blob/main/demo.py
"""
import argparse
import os
import sys
import random

import numpy as np
import torch
import torch.backends.cudnn as cudnn
import gradio as gr

from koala.common.config import Config
from koala.common.dist_utils import get_rank
from koala.common.registry import registry
from koala.conversation.conversation_video import Chat, Conversation, default_conversation,SeparatorStyle,conv_llava_llama_2
import decord
decord.bridge.set_bridge('torch')

#%%
# imports modules for registration
from koala.datasets.builders import *
from koala.models import *
from koala.processors import *
from koala.runners import *
from koala.tasks import *

#%%
def parse_args():
    parser = argparse.ArgumentParser(description="Demo")
    #parser.add_argument("--cfg-path", required=True, help="path to configuration file.")
    parser.add_argument("--cfg-path", type=str, default='./koala/eval_configs/conversation_demo.yaml', help="path to configuration file.")
    parser.add_argument("--gpu-id", type=int, default=0, help="specify the gpu to load the model.")
    parser.add_argument("--model_type", type=str, default='llama_v2', help="specify LLM")
    #parser.add_argument('--pretrained_weight_path', type=str, default="./ckpt/finetuned_model.pth", metavar='PWP',
    #                help='path to pretrained weight path')
    parser.add_argument('--pretrained_weight_path', type=str, default="/net/ivcfs5/mnt/data/reuben/procedural_video_understanding/models/CVPR2024-final-release/all_training_weights/instruction_ft/merged_weight_0.001_agg_without-top-final-global-prompts-region-segment-full-dis-spatiotemporal-prompts-attn-early-attn-linear-learned_freeze_linear_True_epochs_3_bs_16_warmup_steps_205_init_lr_3e-05_accum_steps_1_segments_4_num_frames_16_model/epoch_2_full.pth", metavar='PWP', help='path to pretrained weight path')
    parser.add_argument('--num_frames_per_clip', type=int, default=16, metavar='NPPC',
                    help='specify how frames to use per clip')
    parser.add_argument('--num_segments', type=int, default=4, metavar='NS',
                        help='specify number of video segments')
    parser.add_argument('--hierarchical_agg_function', type=str, default="without-top-final-global-prompts-region-segment-full-dis-spatiotemporal-prompts-attn-early-attn-linear-learned", metavar='HAF',
                        help='specify function to merge global and clip visual representations')

    parser.add_argument(
        "--options",
        nargs="+",
        help="override some settings in the used config, the key-value pair "
        "in xxx=yyy format will be merged into config file (deprecate), "
        "change to --cfg-options instead.",
    )
    args = parser.parse_args()
    return args


def setup_seeds(config):
    seed = config.run_cfg.seed + get_rank()

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    cudnn.benchmark = False
    cudnn.deterministic = True


# ========================================
#             Model Initialization
# ========================================

print('Initializing Chat')
args = parse_args()
cfg = Config(args)

model_config = cfg.model_cfg
model_config.device_8bit = args.gpu_id
model_cls = registry.get_model_class(model_config.arch)
model = model_cls.from_config(model_config).to('cuda:{}'.format(args.gpu_id))

model.num_frames_per_clip = args.num_frames_per_clip
model.num_segments = args.num_segments
model.hierarchical_agg_function = args.hierarchical_agg_function
model.global_region_embed_weight = None

model.initialize_visual_agg_function()

best_checkpoint = torch.load(args.pretrained_weight_path, map_location='cpu')['model_state_dict']
pretrained_dict = {}
for k, v in best_checkpoint.items():
    pretrained_dict[k.replace('module.', '')] = v

model_dict = model.state_dict()
model_dict.update(pretrained_dict)
model.load_state_dict(model_dict)
model.cuda().eval()

vis_processor_cfg = cfg.datasets_cfg.webvid.vis_processor.train
vis_processor = registry.get_processor_class(vis_processor_cfg.name).from_config(vis_processor_cfg)
chat = Chat(model, vis_processor, device='cuda:{}'.format(args.gpu_id))
print('Initialization Finished')

# ========================================
#             Gradio Setting
# ========================================

def gradio_reset(chat_state, img_list):
    if chat_state is not None:
        chat_state.messages = []
    if img_list is not None:
        img_list = []
    return None, gr.update(value=None, interactive=True), gr.update(placeholder='Please upload your video first', interactive=False),gr.update(value="Upload & Start Chat", interactive=True), chat_state, img_list

def upload_imgorvideo(gr_video, text_input, chat_state, chatbot):
    if args.model_type == 'vicuna':
        chat_state = default_conversation.copy()
    else:
        chat_state = conv_llava_llama_2.copy()
    
    print(gr_video)
    chatbot = chatbot + [((gr_video,), None)]
    chat_state.system =  "You are able to understand the visual content that the user provides. Follow the instructions carefully and explain your answers in detail."
    img_list = []
    llm_message = chat.upload_video_without_audio(gr_video, chat_state, img_list)
    return gr.update(interactive=False), gr.update(interactive=True, placeholder='Type and press Enter'), gr.update(value="Start Chatting", interactive=False), chat_state, img_list,chatbot

def gradio_ask(user_message, chatbot, chat_state):
    if len(user_message) == 0:
        return gr.update(interactive=True, placeholder='Input should not be empty!'), chatbot, chat_state
    chat.ask(user_message, chat_state)
    chatbot = chatbot + [[user_message, None]]
    return '', chatbot, chat_state


def gradio_answer(chatbot, chat_state, img_list, num_beams, temperature):
    llm_message = chat.answer(conv=chat_state,
                              img_list=img_list,
                              num_beams=num_beams,
                              temperature=temperature,
                              max_new_tokens=300,
                              max_length=2000)[0]
    chatbot[-1][1] = llm_message
    return chatbot, chat_state, img_list

title = """
<h1 align="center">Koala: Key frame-conditioned long video-LLM</h1>

<h5 align="center">  Introduction: We introduce a Koala video model that is connected with a Large Language Model to understand \
                    and answer questions about long videos. </h5> 

<div style='display:flex; gap: 0.25rem; '>
<a href='https://huggingface.co/spaces/rxtan/Koala-video-llm'><img src='https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue'></a> 
<a href='https://arxiv.org/abs/2404.04346'><img src='https://img.shields.io/badge/Paper-PDF-red'></a>
</div>


Thank you for using the Koala video-LLM Page! If you have any questions or feedback, feel free to contact us. 
Current online demo uses the 7B version of Llama-2 due to resource limitations.


"""

Note_markdown = ("""
### We note that our Koala model may be limited at understanding videos from rare domains. Due to the pretraining data, the \
    model may be susceptible to hallucinations
We would like to acknowledge the Video-LLama repository which we copied the demo layout from.

**Boston University**
""")

cite_markdown = ("""
""")

with gr.Blocks() as demo:
    gr.Markdown(title)

    with gr.Row():
        with gr.Column(scale=0.5):
            video = gr.Video()
            #image = gr.Image(type="filepath")
            image = None
            #gr.Markdown(case_note_upload)

            upload_button = gr.Button(value="Upload & Start Chat", interactive=True, variant="primary")
            clear = gr.Button("Restart")
            
            num_beams = gr.Slider(
                minimum=1,
                maximum=10,
                value=1,
                step=1,
                interactive=True,
                label="beam search numbers)",
            )
            
            temperature = gr.Slider(
                minimum=0.1,
                maximum=2.0,
                value=1.0,
                step=0.1,
                interactive=True,
                label="Temperature",
            )

            audio = gr.Checkbox(interactive=True, value=False, label="Audio")
            gr.Markdown(Note_markdown)
        with gr.Column():
            chat_state = gr.State()
            img_list = gr.State()
            chatbot = gr.Chatbot(label='Koala video-LLM')
            text_input = gr.Textbox(label='User', placeholder='Please upload your video first.', interactive=False)
            
        
    gr.Markdown(cite_markdown)

    upload_button.click(upload_imgorvideo, [video, text_input, chat_state, chatbot], [video, text_input, upload_button, chat_state, img_list, chatbot])
    
    text_input.submit(gradio_ask, [text_input, chatbot, chat_state], [text_input, chatbot, chat_state]).then(
        gradio_answer, [chatbot, chat_state, img_list, num_beams, temperature], [chatbot, chat_state, img_list]
    )
    clear.click(gradio_reset, [chat_state, img_list], [chatbot, video, text_input, upload_button, chat_state, img_list], queue=False)

demo.launch(share=False, debug=True)
