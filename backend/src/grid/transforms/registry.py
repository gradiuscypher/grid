from grid.transforms.base import BaseTransform
from grid.transforms.builtins.crtsh_subdomains import CrtShSubdomainsTransform
from grid.transforms.builtins.dns_forward import DnsForwardTransform
from grid.transforms.builtins.dns_reverse import DnsReverseTransform

BUILTIN_TRANSFORMS: dict[str, BaseTransform] = {
    transform.descriptor.id: transform
    for transform in (DnsForwardTransform(), DnsReverseTransform(), CrtShSubdomainsTransform())
}
