/// Business rule that classifies a venue's crowdedness level from its popularity
/// score. Nightlife venues (bar/pub/nightclub) use lower thresholds since they are
/// naturally busier late at night; this keeps the thresholds editable by a business
/// analyst via the Rule Editor UI instead of buried in Python code.
Class PopHeat.Rule.HeatLevel Extends Ens.Rule.Definition
{

Parameter RuleAssistClass = "Ens.Rule.GeneralBusinessRuleAssist";

XData RuleDefinition [ XMLNamespace = "http://www.intersystems.com/rule" ]
{
<ruleDefinition alias="" context="PopHeat.Rule.Context">
<ruleSet name="" effectiveBegin="" effectiveEnd="">
<rule name="NightlifeCritical" disabled="false">
<when condition="(Category=&quot;bar&quot;||Category=&quot;pub&quot;||Category=&quot;nightclub&quot;)&amp;&amp;(Popularity&gt;=0.6)">
<return>"CRITICO"</return>
</when>
</rule>
<rule name="NightlifeHigh" disabled="false">
<when condition="(Category=&quot;bar&quot;||Category=&quot;pub&quot;||Category=&quot;nightclub&quot;)&amp;&amp;(Popularity&gt;=0.4)">
<return>"ALTO"</return>
</when>
</rule>
<rule name="NightlifeMedium" disabled="false">
<when condition="(Category=&quot;bar&quot;||Category=&quot;pub&quot;||Category=&quot;nightclub&quot;)&amp;&amp;(Popularity&gt;=0.2)">
<return>"MEDIO"</return>
</when>
</rule>
<rule name="NightlifeLow" disabled="false">
<when condition="Category=&quot;bar&quot;||Category=&quot;pub&quot;||Category=&quot;nightclub&quot;">
<return>"BAIXO"</return>
</when>
</rule>
<rule name="DaytimeCritical" disabled="false">
<when condition="Popularity&gt;=0.75">
<return>"CRITICO"</return>
</when>
</rule>
<rule name="DaytimeHigh" disabled="false">
<when condition="Popularity&gt;=0.5">
<return>"ALTO"</return>
</when>
</rule>
<rule name="DaytimeMedium" disabled="false">
<when condition="Popularity&gt;=0.25">
<return>"MEDIO"</return>
</when>
</rule>
<rule name="DaytimeLow" disabled="false">
<when condition="1">
<return>"BAIXO"</return>
</when>
</rule>
</ruleSet>
</ruleDefinition>
}

}
