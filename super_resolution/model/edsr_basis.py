"""
Author: Yawei Li
Date: 20/08/2019
Basis learning method applied to EDSR for ICCV2019 paper.
"""

from model import common
import torch.nn as nn
import torch


def make_model(args, parent=False):
    return EDSR_Basis(args)


class EDSR_Basis(nn.Module):
    def __init__(self, args, conv=common.default_conv):
        super(EDSR_Basis, self).__init__()

        basis_size = args.basis_size
        n_basis = args.n_basis
        share_basis = args.share_basis
        n_resblock = args.n_resblocks
        n_feats = args.n_feats
        scale = args.scale[0]
        bn_every = args.bn_every

        kernel_size = 3
        act = nn.ReLU(True)

        rgb_mean = (0.4488, 0.4371, 0.4040)
        rgb_std = (1.0, 1.0, 1.0)

        # define head module
        m_head = [conv(args.n_colors, n_feats, kernel_size)]
        # define body module
        m_body = [common.ResBlock_Basis(n_feats, kernel_size, basis_size, n_basis, share_basis, conv=common.conv_basis,
                                        act=act, res_scale=args.res_scale, bn_every=bn_every) for _ in range(n_resblock)]
        m_body.append(conv(n_feats, n_feats, kernel_size))
        # define tail module
        m_tail = [
            common.Upsampler(conv, scale, n_feats, act=False),
            conv(n_feats, args.n_colors, kernel_size)
        ]

        self.sub_mean = common.MeanShift(args.rgb_range, rgb_mean, rgb_std)
        self.head = nn.Sequential(*m_head)
        self.body = nn.Sequential(*m_body)
        self.tail = nn.Sequential(*m_tail)
        self.add_mean = common.MeanShift(args.rgb_range, rgb_mean, rgb_std, 1)
        # from IPython import embed; embed()
    def forward(self, x):
        x = self.sub_mean(x)
        x = self.head(x)
        res = self.body(x)
        x = self.tail(res + x)
        x = self.add_mean(x)

        return x

    def load_state_dict(self, state_dict, strict=True):
        own_state = self.state_dict()
        for name, param in state_dict.items():
            if name in own_state:
                if isinstance(param, nn.Parameter):
                    param = param.data
                try:
                    own_state[name].copy_(param)
                except Exception:
                    if name.find('tail') == -1:
                        raise RuntimeError('While copying the parameter named {}, '
                                           'whose dimensions in the model are {} and '
                                           'whose dimensions in the checkpoint are {}.'
                                           .format(name, own_state[name].size(), param.size()))
            elif strict:
                if name.find('tail') == -1:
                    raise KeyError('unexpected key "{}" in state_dict'
                                   .format(name))