_base_ = ['mmdet3d::_base_/default_runtime.py']

custom_imports = dict(
    imports=['projects.TPVFormer.tpvformer'], allow_failed_imports=False)

dataset_type = 'NuScenesSegDataset'
data_root = 'data/nuscenes/'
data_prefix = dict(
    pts='samples/LIDAR_TOP',
    pts_semantic_mask='lidarseg/v1.0-trainval',
    CAM_FRONT='samples/CAM_FRONT',
    CAM_FRONT_LEFT='samples/CAM_FRONT_LEFT',
    CAM_FRONT_RIGHT='samples/CAM_FRONT_RIGHT',
    CAM_BACK='samples/CAM_BACK',
    CAM_BACK_RIGHT='samples/CAM_BACK_RIGHT',
    CAM_BACK_LEFT='samples/CAM_BACK_LEFT')

backend_args = None

train_pipeline = [
    dict(
        type='BEVLoadMultiViewImageFromFiles',
        to_float32=False,
        color_type='unchanged',
        num_views=6,
        backend_args=backend_args),
    dict(
        type='LoadPointsFromFile',
        coord_type='LIDAR',
        load_dim=5,
        use_dim=3,
        backend_args=backend_args),
    dict(
        type='LoadAnnotations3D',
        with_bbox_3d=False,
        with_label_3d=False,
        with_seg_3d=True,
        with_attr_label=False,
        seg_3d_dtype='np.uint8'),
    dict(type='PhotoMetricDistortionMultiViewImage'),
    dict(type='SegLabelMapping'),
    dict(
        type='Pack3DDetInputs',
        keys=['img', 'points', 'pts_semantic_mask'],
        meta_keys=['lidar2img'])
]

val_pipeline = [
    dict(
        type='BEVLoadMultiViewImageFromFiles',
        to_float32=False,
        color_type='unchanged',
        num_views=6,
        backend_args=backend_args),
    dict(
        type='LoadPointsFromFile',
        coord_type='LIDAR',
        load_dim=5,
        use_dim=3,
        backend_args=backend_args),
    dict(
        type='LoadAnnotations3D',
        with_bbox_3d=False,
        with_label_3d=False,
        with_seg_3d=True,
        with_attr_label=False,
        seg_3d_dtype='np.uint8'),
    dict(type='SegLabelMapping'),
    dict(
        type='Pack3DDetInputs',
        keys=['img', 'points', 'pts_semantic_mask'],
        meta_keys=['lidar2img'])
]

test_pipeline = val_pipeline

train_dataloader = dict(
    batch_size=1,
    num_workers=1,
    persistent_workers=True,
    drop_last=True,
    sampler=dict(type='DefaultSampler', shuffle=False),
    dataset=dict(
        type=dataset_type,
        data_root=data_root,
        data_prefix=data_prefix,
        ann_file='seg_pkl_folder/nuscenes_infos_train_fp64.pkl',
        pipeline=train_pipeline,
        test_mode=False))

val_dataloader = dict(
    batch_size=1,
    num_workers=1,
    persistent_workers=True,
    drop_last=False,
    sampler=dict(type='DefaultSampler', shuffle=False),
    dataset=dict(
        type=dataset_type,
        data_root=data_root,
        data_prefix=data_prefix,
        ann_file='seg_pkl_folder/nuscenes_infos_val_fp64.pkl',
        pipeline=val_pipeline,
        test_mode=True))

test_dataloader = val_dataloader

val_evaluator = dict(type='SegMetric')

test_evaluator = val_evaluator

vis_backends = [dict(type='LocalVisBackend'),]
# dict(type='WandbVisBackend')]
#vis_backends = [dict(type='LocalVisBackend'), dict(type='WandbVisBackend')]
visualizer = dict(
    type='Det3DLocalVisualizer', vis_backends=vis_backends, name='visualizer')

optim_wrapper = dict(
    type='OptimWrapper',
    optimizer=dict(type='AdamW', lr=2e-4, weight_decay=0.01),
    paramwise_cfg=dict(custom_keys={
        'backbone': dict(lr_mult=0.1),
    }),
    clip_grad=dict(max_norm=35, norm_type=2),
)

occupancy = True 
lovasz_input = 'voxel'
ce_input = 'voxel'

point_cloud_range = [-51.2, -51.2, -5.0, 51.2, 51.2, 3.0]

_dim_ = 256 
num_heads = 4
_pos_dim_ = _dim_ // 2
_ffn_dim_ = _dim_ * 2
_num_levels_ = 4
_num_cams_ = 6

tpv_h_ = 100
tpv_w_ = 100
tpv_z_ = 8
scale_h = 1
scale_w = 1
scale_z = 1
tpv_encoder_layers = 3 
num_points_in_pillar = [4, 32, 32]
num_points = [8, 64, 64]

hybrid_attn_anchors = 16
grid_shape = [tpv_h_ * scale_h, tpv_w_ * scale_w, tpv_z_ * scale_z]

model = dict(
    type='TPVFormerOCC',
    data_preprocessor=dict(
        type='TPVFormerDataPreprocessor',
        pad_size_divisor=32,
        mean=[103.530, 116.280, 123.675],
        std=[1.0, 1.0, 1.0],
        voxel=True,
        voxel_type='cylindrical',
        voxel_layer=dict(
            grid_shape=grid_shape,
            point_cloud_range=point_cloud_range,
            max_num_points=-1,
            max_voxels=-1,
        ),
        # batch_augments=None), # TODO (chirs)
        batch_augments=[
            dict(
                type='GridMask',
                use_h=True,
                use_w=True,
                rotate=1,
                offset=False,
                ratio=0.5,
                mode=1,
                prob=0.7)
        ]),
    backbone=dict(
        type='mmdet.ResNet',
        depth=101,
        num_stages=4,
        out_indices=(1, 2, 3),
        frozen_stages=1,
        norm_cfg=dict(type='BN2d', requires_grad=False),
        norm_eval=True,
        style='caffe',
        dcn=dict(
            type='DCNv2', deform_groups=1, fallback_on_stride=False
        ),  # original DCNv2 will print log when perform load_state_dict
        stage_with_dcn=(False, False, True, True),
        init_cfg=None,),
    neck=dict(
        type='mmdet.FPN',
        in_channels=[512, 1024, 2048],
        out_channels=_dim_,
        start_level=0,
        add_extra_convs='on_output',
        num_outs=4,
        relu_before_extra_convs=True,
        init_cfg=None,),
    encoder=dict(
        type='TPVFormerOCCEncoder',
        tpv_h=tpv_h_,
        tpv_w=tpv_w_,
        tpv_z=tpv_z_,
        num_layers=tpv_encoder_layers,
        pc_range=point_cloud_range,
        num_points_in_pillar=num_points_in_pillar,
        num_points_in_pillar_cross_view=[16, 16, 16],
        return_intermediate=False,
        transformerlayers=dict(
            type='TPVFormerOCCLayer',
            attn_cfgs=[
                dict(
                    type='TPVFormerOCCCrossViewHybridAttention',
                    embed_dims=_dim_,
                    num_levels=1,
                    dropout=0.1),
                dict(
                    type='TPVFormerOCCImageCrossAttention',
                    pc_range=point_cloud_range,
                    dropout=0.1,
                    deformable_attention=dict(
                         type='TPVFormerOCCMSDeformableAttention3D',
                         dropout=0.1,
                         embed_dims=_dim_,
                         num_points=num_points,
                         num_z_anchors=num_points_in_pillar,
                         num_levels=_num_levels_,
                         floor_sampling_offset=False,
                         tpv_h=tpv_h_,
                         tpv_w=tpv_w_,
                         tpv_z=tpv_z_,
                    ),
                    embed_dims=_dim_,
                    tpv_h=tpv_h_,
                    tpv_w=tpv_w_,
                    tpv_z=tpv_z_,
                )
            ],
            feedforward_channels=_ffn_dim_,
            ffn_dropout=0.1,
            operation_order=('self_attn', 'norm', 'cross_attn', 'norm',
                             'ffn', 'norm')),
        embed_dims=_dim_,
        positional_encoding=dict(
            type='LearnedPositionalEncoding',
            num_feats=_pos_dim_,
            row_num_embed=tpv_h_,
            col_num_embed=tpv_w_,
        ),
    ),
    decode_head=dict(
        type='TPVFormerOCCDecoder',
        tpv_h=tpv_h_,
        tpv_w=tpv_w_,
        tpv_z=tpv_z_,
        num_classes=18,
        in_dims=_dim_,
        hidden_dims=2 * _dim_,
        out_dims=_dim_,
        scale_h=scale_h,
        scale_w=scale_w,
        scale_z=scale_z,
        loss_ce=dict(
            type='mmdet.CrossEntropyLoss',
            use_sigmoid=False,
            class_weight=None,
            avg_non_ignore=True,
            loss_weight=1.0),
        loss_lovasz=dict(type='LovaszLoss', loss_weight=1.0, reduction='none'),
        ignore_index=0
    ),
)

train_cfg = dict(type='EpochBasedTrainLoop', max_epochs=24, val_interval=2)
val_cfg = dict(type='ValLoop')
test_cfg = dict(type='TestLoop')
