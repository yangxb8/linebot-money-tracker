"use client";

import { forwardRef } from "react";
import type { CategoryNode } from "@/lib/categories/types";

type Props = {
  categories: CategoryNode[];
  value: string;
  onChange: (categoryNodeId: string) => void;
  className?: string;
  placeholder?: string;
  autoFocus?: boolean;
  disabled?: boolean;
};

export const CategoryNodeSelect = forwardRef<HTMLSelectElement, Props>(
  function CategoryNodeSelect(
    { categories, value, onChange, className, placeholder, autoFocus, disabled },
    ref,
  ) {
    const l1Nodes = categories.filter((node) => node.level === 1);
    const l2Nodes = categories.filter((node) => node.level === 2);

    return (
      <select
        ref={ref}
        value={value}
        autoFocus={autoFocus}
        disabled={disabled}
        onClick={(event) => event.stopPropagation()}
        onChange={(event) => onChange(event.target.value)}
        className={className}
      >
        {placeholder ? <option value="">{placeholder}</option> : null}
        {l1Nodes.map((l1) => (
          <optgroup key={l1.id} label={l1.name_ja}>
            <option value={l1.id}>{l1.name_ja}</option>
            {l2Nodes
              .filter((l2) => l2.parent_id === l1.id)
              .map((l2) => (
                <option key={l2.id} value={l2.id}>
                  {l2.name_ja}
                </option>
              ))}
          </optgroup>
        ))}
      </select>
    );
  },
);
