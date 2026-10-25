import 'package:flutter/material.dart';
import 'sync_store.dart';

void main() => runApp(const OmniCodexApp());
class OmniCodexApp extends StatefulWidget { const OmniCodexApp({super.key}); State<OmniCodexApp> createState()=>_AppState(); }
class _AppState extends State<OmniCodexApp> {
  SyncStore? store; String? error;
  @override void initState(){ super.initState(); _loginAndRestore(); }
  Future<void> _loginAndRestore() async { try { const token=String.fromEnvironment('OMNI_ACCESS_TOKEN'); if(token.isEmpty) throw Exception('Pass --dart-define=OMNI_ACCESS_TOKEN=<JWT>'); final s=SyncStore(SyncStore.apiBaseUrl,token); await s.rehydrate(); if(mounted)setState(()=>store=s); } catch(e){ if(mounted)setState(()=>error='$e'); } }
  @override Widget build(BuildContext c){ if(error!=null)return MaterialApp(home:Scaffold(body:Center(child:Text(error!)))); if(store==null)return const MaterialApp(home:Scaffold(body:Center(child:CircularProgressIndicator()))); return MaterialApp(home:Scaffold(appBar:AppBar(title:const Text('OmniCodex')),body:Row(children:[Expanded(child:ListView(children:store!.projects.values.map((p)=>ListTile(title:Text(p['name'] as String))).toList())),const VerticalDivider(),const Expanded(child:Center(child:Text('Chat / server dashboard')))]))); }
}
