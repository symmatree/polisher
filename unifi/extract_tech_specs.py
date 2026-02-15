#!/usr/bin/env python3
"""
Extract technical specifications from UniFi Tech Specs pages.

The techspecs.ui.com pages embed all data in a __NEXT_DATA__ script tag
in the initial HTML response, so we can extract it with a simple HTTP request.
"""

import json
import re
import sys
import urllib.request
from typing import Dict, Any, Optional


def extract_tech_specs(url: str) -> Optional[Dict[str, Any]]:
    """
    Extract technical specifications from a techspecs.ui.com page.
    
    Args:
        url: The full URL to the tech specs page
        
    Returns:
        Dictionary with section labels as keys and feature data as values,
        or None if extraction fails
    """
    try:
        # Fetch the page
        with urllib.request.urlopen(url) as response:
            html = response.read().decode('utf-8')
        
        # Extract the __NEXT_DATA__ JSON
        match = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            html,
            re.DOTALL
        )
        
        if not match:
            print(f"Warning: Could not find __NEXT_DATA__ in {url}", file=sys.stderr)
            return None
        
        # Parse the JSON
        data = json.loads(match.group(1))
        
        # Navigate to the technical specification data
        spec = data.get('props', {}).get('pageProps', {}).get('product', {}).get('technicalSpecification', {})
        sections = spec.get('sections', [])
        
        # Extract data from all sections except Layer 2 Features
        result = {}
        for section in sections:
            section_label = section['section']['label']
            if section_label == 'Layer 2 Features':
                continue
            
            section_data = {}
            for feature_entry in section.get('features', []):
                feature = feature_entry.get('feature', {})
                if feature.get('parentId') is None:  # Top-level features only
                    label = feature.get('label', '')
                    
                    # Handle different feature types
                    if 'value' in feature_entry and feature_entry['value']:
                        section_data[label] = feature_entry['value']
                    elif feature_entry.get('flag') == 'True':
                        section_data[label] = 'Yes'
                    elif 'features' in feature_entry:  # Nested features (like Port Layout)
                        nested_data = {}
                        for sub_feature in feature_entry.get('features', []):
                            sub_label = sub_feature.get('feature', {}).get('label', '')
                            if 'value' in sub_feature and sub_feature['value']:
                                nested_data[sub_label] = sub_feature['value']
                            elif sub_feature.get('flag') == 'True':
                                nested_data[sub_label] = 'Yes'
                        if nested_data:
                            section_data[label] = nested_data
            
            if section_data:
                result[section_label] = section_data
        
        return result
        
    except Exception as e:
        print(f"Error extracting specs from {url}: {e}", file=sys.stderr)
        return None


def format_specs_for_markdown(specs: Dict[str, Any]) -> str:
    """
    Format the extracted specs as a Markdown section.
    
    Args:
        specs: Dictionary of section labels to feature data
        
    Returns:
        Markdown-formatted string
    """
    if not specs:
        return ""
    
    lines = ["## Technical Specifications", ""]
    
    for section_label, section_data in specs.items():
        lines.append(f"### {section_label}")
        lines.append("")
        
        for label, value in section_data.items():
            if isinstance(value, dict):
                # Handle nested data (like Port Layout)
                lines.append(f"- **{label}**:")
                for sub_label, sub_value in value.items():
                    lines.append(f"  - {sub_label}: {sub_value}")
            else:
                # Handle simple values
                # Replace newlines with spaces for cleaner output
                clean_value = str(value).replace('\n', ' ').strip()
                lines.append(f"- **{label}**: {clean_value}")
        
        lines.append("")
    
    lines.append("*Technical specifications extracted from UniFi Tech Specs pages by parsing the embedded `__NEXT_DATA__` JSON from the page HTML.*")
    lines.append("")
    
    return "\n".join(lines)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: extract_tech_specs.py <url>", file=sys.stderr)
        sys.exit(1)
    
    url = sys.argv[1]
    specs = extract_tech_specs(url)
    
    if specs:
        # Output as JSON for programmatic use
        if '--json' in sys.argv:
            print(json.dumps(specs, indent=2))
        else:
            # Output as Markdown
            print(format_specs_for_markdown(specs))
    else:
        sys.exit(1)
