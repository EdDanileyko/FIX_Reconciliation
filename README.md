The primary objective of this script is to reconcile inbound (client->trading system) and outbound (trading system->exchange)
order fills to determine if there are any breaks between the two "sides" of the trading system.

I am looking to identify some common issues that relate to FIX messaging through a trading system,
such as:
    - fills present in the outbound logs that may not be present in the inbound logs.
        This might indicate fills received from the exchange (outbound) were not sent back to the
        client (inbound). This is common when inbound FIX sessions flap.
    - fills identified in the client-side FIX logs are not present in the available exchange FIX logs.
        This might indicate incomplete data or a configuration issue with the client FIX session.
    - orders or fills in either of the logs do not contain the necessary tags or are otherwise not
        parsable. This might point to any number of issues with configuration, data corruption, etc

1) Parse the inbound and outbound FIX log.
    Use a CSV file linking parent and child IDs (ids.csv)
2) When run, process should output a readable summary to the screen (issues only)
    and a comprehensive CSV written to a file (verbose)

EXAMPLE:

inbound gateway Log:
	new order single:

		20170803-22:03:04.623 : 8=FIX.4.2|9=229|35=D|34=29|49=TEST|50=Cert|52=20170803-22:03:04.594|56=PRODCH|1=TEST|11=180304593902ZNU712morntestbolt18.03.01.d03.cme.probe|21=2|22=8|38=5|40=1|44=0|48=ZNU7|54=1|55=ZNU7|59=0|60=20170803-22:03:04|100=2|847=1002|8561=8|10=156|
	
	ack:
		
		20170803-22:03:04.646 : 8=FIX.4.2|9=306|35=8|34=29|49=PRODCH|52=20170803-22:03:04.646|56=TEST|57=Cert|1=TEST|6=0|11=180304593902ZNU712morntestbolt18.03.01.d03.cme.probe|14=0|17=B_CH1OU4QL42|20=0|22=8|31=0|32=0|37=00000024__PRODCH|38=5|39=0|48=ZNU7|54=1|55=ZNU7|60=20170803-22:03:04.644|76=BAML|113=Y|150=0|151=5|167=FUT|200=201709|10=186|
	
	full fill:
		
		20170803-22:06:01.023 : 8=FIX.4.2|9=320|35=8|34=193|49=PRODCH|52=20170803-22:06:01.023|56=TEST|57=Cert|1=TEST|6=126.375|11=180304593902ZNU712morntestbolt18.03.01.d03.cme.probe|14=5|17=B_CH1OU4QQ15A|20=0|22=8|31=126.375|32=5|37=00000024__PRODCH|38=5|39=2|48=ZNU7|54=1|55=ZNU7|60=20170803-22:06:01.022|76=BAML|113=Y|150=2|151=0|167=FUT|200=201709|10=142|

ids map:

	ordID,primOrdID,parentOrdId
	B_CH1OU4QLV3,B_CH1OU4QLV3,00000024__PRODCH

outbound gateway log:

	new order single:

		20170803-22:03:31.778 : 8=FIX.4.2|9=238|35=D|34=28|49=TEOUTBOUND|50=-CH5|52=20170803-22:03:31.778|56=SIM_CME|57=G|142=US,NY|1=TEST|11=B_CH1OU4QLV3|21=1|38=5|40=2|44=126.375|54=1|55=ZNU7|59=0|60=20170803-22:03:31|100=CME|107=ZNU7|167=FUT|204=0|1028=N|9702=4|12000=TEOUTBOUND|10=152|

	ack:

		20170803-22:03:31.780 : 8=FIX.4.2|9=253|35=8|34=15|49=SIM_CME|52=20170803-22:03:31.777|56=TEOUTBOUND|57=-CH5|1=TEST|6=0|11=B_CH1OU4QLV3|14=0|17=exe_2|20=0|31=0|32=0|37=SN00000002__simgway|38=5|39=0|40=2|44=126.375|54=1|55=ZNU7|60=20170803-22:03:31.777|113=Y|150=0|151=5|167=FUT|200=201709|10=238|

	full fill:

		20170803-22:06:01.022 : 8=FIX.4.2|9=266|35=8|34=212|49=SIM_CME|52=20170803-22:06:01.019|56=TEOUTBOUND|57=-CH5|1=TEST|6=126.375|11=B_CH1OU4QLV3|14=5|17=exe_5|20=0|31=126.375|32=5|37=SN00000002__simgway|38=5|39=2|40=2|44=126.375|54=1|55=ZNU7|60=20170803-22:06:01.019|113=Y|150=2|151=0|167=FUT|200=201709|10=131|	
