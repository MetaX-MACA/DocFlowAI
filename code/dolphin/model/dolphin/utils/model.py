# 2025 - Modified by MetaX Integrated Circuits (Shanghai) Co., Ltd. All Rights Reserved.
"""
Copyright (c) 2022-present NAVER Corp.
Copyright (c) 2025 Bytedance Ltd. and/or its affiliates.
MIT License
This file has been modified by [ByteDance Ltd. and/or its affiliates] on 20250118.
The original file available at https://github.com/clovaai/donut/blob/master/donut/model.py was released under the MIT license.
This modified file is released under the same license.
"""

import logging
from collections import defaultdict
from typing import List, Optional

import torch
import torch.nn.functional as F
from PIL import Image
from timm.models.swin_transformer import SwinTransformer
from torch import nn
from transformers import (
    MBartConfig,
    MBartForCausalLM,
    StoppingCriteria,
    StoppingCriteriaList,
)
from transformers.file_utils import ModelOutput
from transformers.modeling_utils import PretrainedConfig, PreTrainedModel


class SwinEncoder(nn.Module):
    r"""
    Encoder based on SwinTransformer
    Set the initial weights and configuration with a pretrained SwinTransformer and then
    modify the detailed configurations

    Args:
        input_size: Input image size (width, height)
        align_long_axis: Whether to rotate image if height is greater than width
        window_size: Window size(=patch size) of SwinTransformer
        encoder_layer: Number of layers of SwinTransformer encoder
        name_or_path: Name of a pretrained model name either registered in huggingface.co. or saved in local.
                      otherwise, `swin_base_patch4_window12_384` will be set (using `timm`).
    """

    def __init__(
        self,
        input_size,
        align_long_axis: bool = False,
        window_size: int = 7,
        encoder_layer: List[int] = [2, 2, 14, 2],
        patch_size: int = [4, 4],
        embed_dim: int = 128,
        num_heads: List[int] = [4, 8, 16, 32],
    ):
        super().__init__()
        if isinstance(input_size, int):
            input_size = [input_size, input_size]
        self.input_size = input_size
        self.align_long_axis = align_long_axis
        self.window_size = window_size
        self.encoder_layer = encoder_layer
        self.patch_size = patch_size
        self.embed_dim = embed_dim
        self.num_heads = num_heads

        self.model = SwinTransformer(
            img_size=self.input_size,
            depths=self.encoder_layer,
            window_size=self.window_size,
            patch_size=self.patch_size,
            embed_dim=self.embed_dim,
            num_heads=self.num_heads,
            num_classes=0,
        )

    def forward(self, x: torch.Tensor, text_embedding: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Args:
            x: (batch_size, num_channels, height, width)
        """
        x = self.model.patch_embed(x)
        x = self.model.pos_drop(x)
        x = self.model.layers(x)
        return x


class LayerNorm(nn.LayerNorm):
    """Subclass torch's LayerNorm to handle fp16."""

    def _set_dtype(self, dtype):
        self._dtype = dtype

    def forward(self, x: torch.Tensor):
        orig_type = x.dtype
        ret = super().forward(x.type(dtype=self._dtype))
        return ret.type(orig_type)


class BARTDecoder(nn.Module):
    """
    Decoder based on Multilingual BART
    Set the initial weights and configuration with a pretrained multilingual BART model,
    and modify the detailed configurations as a Donut decoder

    Args:
        decoder_layer:
            Number of layers of BARTDecoder
        max_position_embeddings:
            The maximum sequence length to be trained
        name_or_path:
            Name of a pretrained model name either registered in huggingface.co. or saved in local,
            otherwise, `facebook/mbart-large-50` will be set (using `transformers`)
    """

    def __init__(
        self,
        tokenizer,
        decoder_layer: int,
        max_position_embeddings: int,
        hidden_dimension: int = 1024,
        **kwargs,
    ):
        super().__init__()
        self.decoder_layer = decoder_layer
        self.max_position_embeddings = max_position_embeddings
        self.hidden_dimension = hidden_dimension

        self.tokenizer = tokenizer

        self.model = MBartForCausalLM(
            config=MBartConfig(
                tie_word_embeddings=True,
                is_decoder=True,
                is_encoder_decoder=False,
                add_cross_attention=True,
                decoder_layers=self.decoder_layer,
                max_position_embeddings=self.max_position_embeddings,
                vocab_size=len(self.tokenizer),
                scale_embedding=True,
                add_final_layer_norm=True,
                d_model=self.hidden_dimension,
            )
        )
        # self.model.config.is_encoder_decoder = True  # to get cross-attention
        self.model.model.decoder.embed_tokens.padding_idx = self.tokenizer.pad_token_id
        self.model.prepare_inputs_for_generation = self.prepare_inputs_for_inference

    def add_special_tokens(self, list_of_tokens: List[str]):
        """
        Add special tokens to tokenizer and resize the token embeddings
        """
        newly_added_num = self.tokenizer.add_special_tokens({"additional_special_tokens": sorted(set(list_of_tokens))})
        if newly_added_num > 0:
            self.model.resize_token_embeddings(len(self.tokenizer))

    def add_tokens(self, list_of_tokens: List[str]):
        """
        Add special tokens to tokenizer and resize the token embeddings
        """
        newly_added_num = self.tokenizer.add_tokens(sorted(set(list_of_tokens)))
        if newly_added_num > 0:
            self.model.resize_token_embeddings(len(self.tokenizer))

    def prepare_inputs_for_inference(
        self,
        input_ids: torch.Tensor,
        encoder_outputs: torch.Tensor,
        past=None,
        past_key_values=None,
        use_cache: bool = None,
        attention_mask: torch.Tensor = None,
        **kwargs,
    ):
        """
        Args:
            input_ids: (batch_size, sequence_length)

        Returns:
            input_ids: (batch_size, sequence_length)
            attention_mask: (batch_size, sequence_length)
            encoder_hidden_states: (batch_size, sequence_length, embedding_dim)
        """
        attention_mask = input_ids.ne(self.tokenizer.pad_token_id).long()
        past = past or past_key_values
        if past is not None:
            input_ids = input_ids[:, -1:]
        output = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "past_key_values": past,
            "use_cache": use_cache,
            "encoder_hidden_states": encoder_outputs.last_hidden_state,
        }
        return output

    def forward(
        self,
        input_ids: torch.LongTensor = None,
        attention_mask: Optional[torch.Tensor] = None,
        encoder_hidden_states: Optional[torch.Tensor] = None,
        past_key_values: Optional[torch.Tensor] = None,
        inputs_embeds: Optional[torch.FloatTensor] = None,
        labels: Optional[torch.Tensor] = None,
        use_cache: bool = None,
        output_attentions: Optional[torch.Tensor] = None,
        output_hidden_states: Optional[torch.Tensor] = None,
        return_dict: bool = None,
    ):
        return self.model.forward(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels,
            encoder_hidden_states=encoder_hidden_states,
            past_key_values=past_key_values,
            inputs_embeds=inputs_embeds,
            use_cache=use_cache,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )

    @staticmethod
    def resize_bart_abs_pos_emb(weight: torch.Tensor, max_length: int) -> torch.Tensor:
        """
        Resize position embeddings
        Truncate if sequence length of MBart backbone is greater than given max_length,
        else interpolate to max_length
        """
        if weight.shape[0] > max_length:
            weight = weight[:max_length, ...]
        else:
            weight = (
                F.interpolate(
                    weight.permute(1, 0).unsqueeze(0),
                    size=max_length,
                    mode="linear",
                    align_corners=False,
                )
                .squeeze(0)
                .permute(1, 0)
            )
        return weight


class DonutConfig(PretrainedConfig):

    def __init__(
        self,
        decoder_layer: int = 10,
        max_position_embeddings: int = None,
        max_length: int = 4096,
        hidden_dimension: int = 1024,
        **kwargs,
    ):
        super().__init__()
        self.decoder_layer = decoder_layer
        self.max_position_embeddings = max_length if max_position_embeddings is None else max_position_embeddings
        self.max_length = max_length
        self.hidden_dimension = hidden_dimension


class RunningVarTorch:
    def __init__(self, L=15, norm=False):
        self.values = None
        self.L = L
        self.norm = norm

    def push(self, x: torch.Tensor):
        assert x.dim() == 1
        if self.values is None:
            self.values = x[:, None]
        elif self.values.shape[1] < self.L:
            self.values = torch.cat((self.values, x[:, None]), 1)
        else:
            self.values = torch.cat((self.values[:, 1:], x[:, None]), 1)

    def variance(self):
        if self.values is None:
            return
        if self.norm:
            return torch.var(self.values, 1) / self.values.shape[1]
        else:
            return torch.var(self.values, 1)


class StoppingCriteriaScores(StoppingCriteria):
    def __init__(self, threshold: float = 0.015, window_size: int = 200):
        super().__init__()
        self.threshold = threshold
        self.vars = RunningVarTorch(norm=True)
        self.varvars = RunningVarTorch(L=window_size)
        self.stop_inds = defaultdict(int)
        self.stopped = defaultdict(bool)
        self.size = 0
        self.window_size = window_size

    @torch.no_grad()
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor):
        last_scores = scores[-1]
        self.vars.push(last_scores.max(1)[0].float().cpu())
        self.varvars.push(self.vars.variance())
        self.size += 1
        if self.size < self.window_size:
            return False

        varvar = self.varvars.variance()
        for b in range(len(last_scores)):
            if varvar[b] < self.threshold:
                if self.stop_inds[b] > 0 and not self.stopped[b]:
                    self.stopped[b] = self.stop_inds[b] >= self.size
                else:
                    self.stop_inds[b] = int(min(max(self.size, 1) * 1.15 + 150 + self.window_size, 4095))
            else:
                self.stop_inds[b] = 0
                self.stopped[b] = False
        return all(self.stopped.values()) and len(self.stopped) > 0


def batch(l, b=15):
    subs = []
    for i in range(len(l) - b):
        subs.append(l[i : i + b])
    return subs


def subdiv(l, b=10):
    subs = []
    for i in range(len(l) - b):
        subs.append(l[: i + b])
    return subs


class DonutModel(PreTrainedModel):
    config_class = DonutConfig
    base_model_prefix = "donut"

    def __init__(self, config: DonutConfig, vision_tower=None, tokenizer=None):
        super().__init__(config)
        self.config = config

        self.tokenizer = tokenizer
        self.vpm = vision_tower

        # build language model
        self.llm = BARTDecoder(
            tokenizer=tokenizer,
            decoder_layer=self.config.decoder_layer,
            max_position_embeddings=self.config.max_position_embeddings,
            hidden_dimension=self.config.hidden_dimension,
        )
        self.ids_to_tokens = {id: content for content, id in self.llm.tokenizer.vocab.items()}

    def get_input_embeddings(self, tensor):
        return self.llm.model.get_input_embeddings()(tensor)

    def forward(
        self,
        inputs: dict,
    ):
        image_tensors = inputs["pixel_values"]
        input_ids = inputs["input_ids"].contiguous()
        attention_mask = inputs["attention_mask"]
        labels = inputs["labels"].contiguous()

        encoder_outputs = self.vpm(
            image_tensors,
            text_embedding=self.llm.model.get_input_embeddings()(input_ids),
        )

        decoder_outputs = self.llm(
            input_ids=input_ids,
            encoder_hidden_states=encoder_outputs,
            attention_mask=attention_mask,
            labels=labels,
        )
        return decoder_outputs

    def get_hidden_states_during_inference(
        self,
        prompt_ids: torch.Tensor,
        image: Image.Image = None,
        image_tensors: Optional[torch.Tensor] = None,
    ):
        if image_tensors is None:
            image_tensors = self.vpm.prepare_input(image).unsqueeze(0)

        if self.device.type != "mps":
            image_tensors = image_tensors.to(next(self.parameters()).dtype)

        image_tensors = image_tensors.to(self.device)
        prompt_ids = prompt_ids.to(self.device)
        all_hidden_states = self.vpm.forward_features(
            image_tensors, text_embedding=self.get_input_embeddings(prompt_ids)
        )
        return all_hidden_states

    def get_attn_weights_during_inference(
        self,
        prompt_ids: torch.Tensor,
        image: Image.Image = None,
        image_tensors: Optional[torch.Tensor] = None,
    ):
        if image_tensors is None:
            image_tensors = self.vpm.prepare_input(image).unsqueeze(0)

        if self.device.type != "mps":
            image_tensors = image_tensors.to(next(self.parameters()).dtype)

        image_tensors = image_tensors.to(self.device)
        prompt_ids = prompt_ids.to(self.device)
        last_attn_score = self.vpm.get_last_layer_cross_attn_score(
            image_tensors, text_embedding=self.get_input_embeddings(prompt_ids)
        )
        return last_attn_score

    def inference(
        self,
        prompt_ids: torch.Tensor,
        image: Image.Image = None,
        image_tensors: Optional[torch.Tensor] = None,
        return_attentions: bool = False,
        early_stopping: bool = True,
    ):
        """
        Generate a token sequence in an auto-regressive manner.

        Args:
            image: input document image (PIL.Image)
            image_tensors: (1, num_channels, height, width)
                convert prompt to tensor if image_tensor is not fed
        """
        output = {
            "predictions": list(),
            "sequences": list(),
            "repeats": list(),
            "repetitions": list(),
        }
        if image is None and image_tensors is None:
            logging.warn("Image not found")
            return output

        if image_tensors is None:
            image_tensors = self.vpm.prepare_input(image).unsqueeze(0)

        if self.device.type != "mps":
            image_tensors = image_tensors.to(next(self.parameters()).dtype)

        image_tensors = image_tensors.to(self.device)
        prompt_ids = prompt_ids.to(self.device)
        last_hidden_state = self.vpm(image_tensors, text_embedding=self.get_input_embeddings(prompt_ids))

        encoder_outputs = ModelOutput(last_hidden_state=last_hidden_state, attentions=None)
        if len(encoder_outputs.last_hidden_state.size()) == 1:
            encoder_outputs.last_hidden_state = encoder_outputs.last_hidden_state.unsqueeze(0)

        # get decoder output
        decoder_output = self.llm.model.generate(
            input_ids=prompt_ids,
            encoder_outputs=encoder_outputs,
            min_length=1,
            max_length=self.config.max_length,
            pad_token_id=self.llm.tokenizer.pad_token_id,
            eos_token_id=self.llm.tokenizer.eos_token_id,
            use_cache=True,
            return_dict_in_generate=True,
            output_scores=True,
            output_attentions=return_attentions,
            do_sample=False,
            num_beams=1,
            stopping_criteria=StoppingCriteriaList([StoppingCriteriaScores()] if early_stopping else []),
        )

        output["repetitions"] = decoder_output.sequences.clone()
        output["sequences"] = decoder_output.sequences.clone()
        output["scores"] = torch.stack(decoder_output.scores, 1).softmax(-1).cpu().max(-1)[0]

        output["repetitions"] = self.llm.tokenizer.batch_decode(output["repetitions"], skip_special_tokens=False)
        return output
