import React from "react";
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "./accordion";
import { genericExamples } from "@/lib/examplesData";

const ExamplesAccordion: React.FC = () => {
  return (
    <div className="w-96">
      <Accordion type="single" collapsible defaultValue="item-0">
        {genericExamples.map((group, gi) => (
          <AccordionItem key={gi} value={`item-${gi}`}>
            <AccordionTrigger>{group.title}</AccordionTrigger>
            <AccordionContent>
              <div className="space-y-3">
                {group.items.map((it, i) => (
                  <div key={i} className="p-2 border rounded-md bg-card">
                    <div className="font-semibold">{it.name}</div>
                    <div className="text-xs text-muted-foreground mt-1">Git Repository: <span className="font-mono text-[11px]">{it.git}</span></div>
                    <div className="text-xs text-muted-foreground mt-1">Start Commit: {it.start_commit ?? (it.from_first_commit ? "first" : "specific")}</div>
                    <div className="text-xs text-muted-foreground mt-1">Fixed Leaps: {String(it.fixed_leaps ?? "-")}</div>
                    <div className="text-xs text-muted-foreground mt-1">Time: {it.time}</div>
                  </div>
                ))}
              </div>
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
};

export default ExamplesAccordion;
