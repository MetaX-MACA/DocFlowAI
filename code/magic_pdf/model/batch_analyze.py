# 2025 - Modified by MetaX Integrated Circuits (Shanghai) Co., Ltd. All Rights Reserved.
import os
import time
import cv2
from loguru import logger
from qwen_vl_utils import process_vision_info
from tqdm import tqdm

from magic_pdf.config.constants import MODEL_NAME
from magic_pdf.model.sub_modules.model_init import AtomModelSingleton
from magic_pdf.model.sub_modules.model_utils import (
    clean_vram, crop_img, get_res_list_from_layout_res, get_coords_and_area)
from magic_pdf.model.sub_modules.ocr.paddleocr2pytorch.ocr_utils import (
    get_adjusted_mfdetrec_res, get_ocr_result_list)

YOLO_LAYOUT_BASE_BATCH_SIZE = 1
MFD_BASE_BATCH_SIZE = 1
MFR_BASE_BATCH_SIZE = 16


class BatchAnalyze:
    def __init__(self, model_manager, batch_ratio: int, show_log, layout_model, formula_enable, table_enable):
        self.model_manager = model_manager
        self.batch_ratio = batch_ratio
        self.show_log = show_log
        self.layout_model = layout_model
        self.formula_enable = formula_enable
        self.table_enable = table_enable

    def __call__(self, images_with_extra_info: list) -> list:
        if len(images_with_extra_info) == 0:
            return []
    
        images_layout_res = []
        layout_start_time = time.time()
        self.model = self.model_manager.get_model(
            ocr=True,
            show_log=self.show_log,
            lang = None,
            layout_model = self.layout_model,
            formula_enable = self.formula_enable,
            table_enable = self.table_enable,
        )

        images = [image for image, _, _ in images_with_extra_info]

        if self.model.layout_model_name == MODEL_NAME.LAYOUTLMv3:
            # layoutlmv3
            for image in images:
                layout_res = self.model.layout_model(image, ignore_catids=[])
                images_layout_res.append(layout_res)
        elif self.model.layout_model_name == MODEL_NAME.DocLayout_YOLO:
            # doclayout_yolo
            layout_images = []
            for image_index, image in enumerate(images):
                layout_images.append(image)

            images_layout_res += self.model.layout_model.batch_predict(
                # layout_images, self.batch_ratio * YOLO_LAYOUT_BASE_BATCH_SIZE
                layout_images, YOLO_LAYOUT_BASE_BATCH_SIZE
            )

        # logger.info(
        #     f'layout time: {round(time.time() - layout_start_time, 2)}, image num: {len(images)}'
        # )

        if self.model.apply_formula:
            # 公式检测
            mfd_start_time = time.time()
            images_mfd_res = self.model.mfd_model.batch_predict(
                # images, self.batch_ratio * MFD_BASE_BATCH_SIZE
                images, MFD_BASE_BATCH_SIZE
            )
            # logger.info(
            #     f'mfd time: {round(time.time() - mfd_start_time, 2)}, image num: {len(images)}'
            # )

            # 公式识别
            mfr_start_time = time.time()
            images_formula_list = self.model.mfr_model.batch_predict(
                images_mfd_res,
                images,
                batch_size=self.batch_ratio * MFR_BASE_BATCH_SIZE,
            )
            mfr_count = 0
            for image_index in range(len(images)):
                images_layout_res[image_index] += images_formula_list[image_index]
                mfr_count += len(images_formula_list[image_index])
            # logger.info(
            #     f'mfr time: {round(time.time() - mfr_start_time, 2)}, image num: {mfr_count}'
            # )

        # 清理显存
        # clean_vram(self.model.device, vram_threshold=8)

        ocr_res_list_all_page = []
        table_res_list_all_page = []
        for index in range(len(images)):
            _, ocr_enable, _lang = images_with_extra_info[index]
            layout_res = images_layout_res[index]
            np_array_img = images[index]

            ocr_res_list, table_res_list, single_page_mfdetrec_res = (
                get_res_list_from_layout_res(layout_res)
            )

            ocr_res_list_all_page.append({'ocr_res_list':ocr_res_list,
                                          'lang':_lang,
                                          'ocr_enable':ocr_enable,
                                          'np_array_img':np_array_img,
                                          'single_page_mfdetrec_res':single_page_mfdetrec_res,
                                          'layout_res':layout_res,
                                          })

            for table_res in table_res_list:
                table_img, _ = crop_img(table_res, np_array_img)
                table_res_list_all_page.append({'table_res':table_res,
                                                'lang':_lang,
                                                'table_img':table_img,
                                              })

        print(f"os.environ['FIGURE_VLM'] {os.environ['FIGURE_VLM']}")
        if os.environ['FIGURE_VLM']=="True":
            for index in range(len(images)):
                layout_res = images_layout_res[index]
                np_array_img = images[index]
                for i, res in enumerate(layout_res):

                    category_id = int(res['category_id'])
                    if category_id == 3:  # figure regions
                        figrure_img, _ = crop_img(res, np_array_img)
                        from base64 import b64encode
                        from PIL import Image
                        import io
                        image_pil = Image.fromarray(figrure_img)
                        byte_arr = io.BytesIO()
                        image_pil.save(byte_arr, format="JPEG")
                        base64 = b64encode(byte_arr.getvalue()).decode('utf-8')
                        # print(f"base64:{base64}")
                        messages = [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "image", "image": f"data:image/jpeg;base64,{base64}"},
                                    {"type": "text", "text": "描述这张图片，图片中有文字就全部提取出来"},
                                ],
                            }
                        ]

                        # Preparation for inference
                        text = self.model.vlm_processor.apply_chat_template(
                            messages, tokenize=False, add_generation_prompt=True
                        )
                        image_inputs, video_inputs = process_vision_info(messages)
                        inputs = self.model.vlm_processor(
                            text=[text],
                            images=image_inputs,
                            videos=video_inputs,
                            padding=True,
                            return_tensors="pt",
                        )
                        inputs = inputs.to("cuda")

                        # Inference
                        generated_ids = self.model.vlm_model.generate(**inputs, max_new_tokens=128)
                        generated_ids_trimmed = [
                            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
                        ]
                        output_text = self.model.vlm_processor.batch_decode(
                            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
                        )
                        print(f"figure desc :{output_text}")

                        fig_desc = output_text[0]
                        res['figure_desc'] = fig_desc
                        res['text'] = fig_desc

        # 文本框检测
        det_start = time.time()
        det_count = 0
        # for ocr_res_list_dict in ocr_res_list_all_page:
        for ocr_res_list_dict in tqdm(ocr_res_list_all_page, desc="OCR-det Predict"):
            # Process each area that requires OCR processing
            _lang = ocr_res_list_dict['lang']
            # Get OCR results for this language's images
            atom_model_manager = AtomModelSingleton()
            ocr_model = atom_model_manager.get_atom_model(
                atom_model_name='ocr',
                ocr_show_log=False,
                det_db_box_thresh=0.3,
                lang=_lang
            )
            for res in ocr_res_list_dict['ocr_res_list']:
                new_image, useful_list = crop_img(
                    res, ocr_res_list_dict['np_array_img'], crop_paste_x=50, crop_paste_y=50
                )
                adjusted_mfdetrec_res = get_adjusted_mfdetrec_res(
                    ocr_res_list_dict['single_page_mfdetrec_res'], useful_list
                )

                # OCR-det
                new_image = cv2.cvtColor(new_image, cv2.COLOR_RGB2BGR)
                ocr_res = ocr_model.ocr(
                    new_image, mfd_res=adjusted_mfdetrec_res, rec=False
                )[0]

                # Integration results
                if ocr_res:
                    ocr_result_list = get_ocr_result_list(ocr_res, useful_list, ocr_res_list_dict['ocr_enable'], new_image, _lang)

                    if res["category_id"] == 3:
                        # ocr_result_list中所有bbox的面积之和
                        ocr_res_area = sum(get_coords_and_area(ocr_res_item)[4] for ocr_res_item in ocr_result_list if 'poly' in ocr_res_item)
                        # 求ocr_res_area和res的面积的比值
                        res_area = get_coords_and_area(res)[4]
                        if res_area > 0:
                            ratio = ocr_res_area / res_area
                            if ratio > 0.25:
                                res["category_id"] = 1
                            else:
                                continue

                    ocr_res_list_dict['layout_res'].extend(ocr_result_list)

            # det_count += len(ocr_res_list_dict['ocr_res_list'])
        # logger.info(f'ocr-det time: {round(time.time()-det_start, 2)}, image num: {det_count}')


        # 表格识别 table recognition
        if self.model.apply_table:
            table_start = time.time()
            # for table_res_list_dict in table_res_list_all_page:
            for table_res_dict in tqdm(table_res_list_all_page, desc="Table Predict"):
                _lang = table_res_dict['lang']
                atom_model_manager = AtomModelSingleton()
                table_model = atom_model_manager.get_atom_model(
                    atom_model_name='table',
                    table_model_name='rapid_table',
                    table_model_path='',
                    table_max_time=400,
                    device='cpu',
                    lang=_lang,
                    table_sub_model_name='slanet_plus'
                )
                html_code, table_cell_bboxes, logic_points, elapse = table_model.predict(table_res_dict['table_img'])
                # 判断是否返回正常
                if html_code:
                    expected_ending = html_code.strip().endswith(
                        '</html>'
                    ) or html_code.strip().endswith('</table>')
                    if expected_ending:
                        table_res_dict['table_res']['html'] = html_code
                    else:
                        logger.warning(
                            'table recognition processing fails, not found expected HTML table end'
                        )
                else:
                    logger.warning(
                        'table recognition processing fails, not get html return'
                    )
            # logger.info(f'table time: {round(time.time() - table_start, 2)}, image num: {len(table_res_list_all_page)}')

        # Create dictionaries to store items by language
        need_ocr_lists_by_lang = {}  # Dict of lists for each language
        img_crop_lists_by_lang = {}  # Dict of lists for each language

        for layout_res in images_layout_res:
            for layout_res_item in layout_res:
                if layout_res_item['category_id'] in [15]:
                    if 'np_img' in layout_res_item and 'lang' in layout_res_item:
                        lang = layout_res_item['lang']

                        # Initialize lists for this language if not exist
                        if lang not in need_ocr_lists_by_lang:
                            need_ocr_lists_by_lang[lang] = []
                            img_crop_lists_by_lang[lang] = []

                        # Add to the appropriate language-specific lists
                        need_ocr_lists_by_lang[lang].append(layout_res_item)
                        img_crop_lists_by_lang[lang].append(layout_res_item['np_img'])

                        # Remove the fields after adding to lists
                        layout_res_item.pop('np_img')
                        layout_res_item.pop('lang')


        if len(img_crop_lists_by_lang) > 0:

            # Process OCR by language
            rec_time = 0
            rec_start = time.time()
            total_processed = 0

            # Process each language separately
            for lang, img_crop_list in img_crop_lists_by_lang.items():
                if len(img_crop_list) > 0:
                    # Get OCR results for this language's images
                    atom_model_manager = AtomModelSingleton()
                    ocr_model = atom_model_manager.get_atom_model(
                        atom_model_name='ocr',
                        ocr_show_log=False,
                        det_db_box_thresh=0.3,
                        lang=lang
                    )
                    ocr_res_list = ocr_model.ocr(img_crop_list, det=False, tqdm_enable=True)[0]

                    # Verify we have matching counts
                    assert len(ocr_res_list) == len(
                        need_ocr_lists_by_lang[lang]), f'ocr_res_list: {len(ocr_res_list)}, need_ocr_list: {len(need_ocr_lists_by_lang[lang])} for lang: {lang}'

                    # Process OCR results for this language
                    for index, layout_res_item in enumerate(need_ocr_lists_by_lang[lang]):
                        ocr_text, ocr_score = ocr_res_list[index]
                        layout_res_item['text'] = ocr_text
                        layout_res_item['score'] = float(f"{ocr_score:.3f}")

                    total_processed += len(img_crop_list)

            rec_time += time.time() - rec_start
            # logger.info(f'ocr-rec time: {round(rec_time, 2)}, total images processed: {total_processed}')



        return images_layout_res
